from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Expense, User
from bot.db.repositories import ExpenseRepo, UserRepo
from bot.keyboards import BANK_LABELS
from bot.services.card_renderer import Participant, render_card

# Валидация
MIN_AMOUNT = 100  # 1₽
MAX_AMOUNT = 100_000_000  # 1 000 000₽
MAX_DESCRIPTION_LEN = 100


@dataclass
class ExpenseResult:
    expense: Expense
    card_image: BytesIO


async def _render_expense_card(session: AsyncSession, expense: Expense) -> BytesIO:
    """Загрузить связанные данные и отрендерить карточку."""
    creator = await UserRepo.get_by_id(session, expense.creator_id)

    # Загрузить пользователей-участников одним запросом
    user_ids = [p.user_id for p in expense.participants]
    if user_ids:
        result = await session.execute(
            select(User).where(User.telegram_id.in_(user_ids))
        )
        users = {u.telegram_id: u for u in result.scalars().all()}
    else:
        users = {}

    creator_name = f"@{creator.username}" if creator.username else creator.first_name

    participants = []
    for p in expense.participants:
        user = users.get(p.user_id)
        name = (
            f"@{user.username}"
            if user and user.username
            else (user.first_name if user else str(p.user_id))
        )
        participants.append(
            Participant(name=name, amount=p.amount, is_settled=p.is_settled)
        )

    return render_card(
        amount=expense.amount,
        description=expense.description,
        creator_name=creator_name,
        bank_label=BANK_LABELS.get(creator.bank_name, creator.bank_name or ""),
        phone=creator.phone or "",
        participants=participants,
    )


def _recalculate_shares(total: int, participants_count: int) -> tuple[int, int]:
    """Вернуть (доля, остаток). Первый участник получает долю + остаток."""
    per_person = total // participants_count
    remainder = total % participants_count
    return per_person, remainder


class ExpenseService:
    @staticmethod
    async def create_expense(
        session: AsyncSession,
        creator_id: int,
        amount: int,
        description: str,
    ) -> ExpenseResult:
        """Создать расход и отрендерить начальную карточку."""
        if not (MIN_AMOUNT <= amount <= MAX_AMOUNT):
            raise ValueError(
                f"Сумма должна быть от {MIN_AMOUNT // 100}₽ до {MAX_AMOUNT // 100:,}₽"
            )
        if not (1 <= len(description) <= MAX_DESCRIPTION_LEN):
            raise ValueError(f"Описание: 1-{MAX_DESCRIPTION_LEN} символов")

        expense = await ExpenseRepo.create(session, creator_id, amount, description)
        eid = expense.id  # Сохранить до expire
        # Сбросить кэш и перезагрузить с relationships
        session.expire_all()
        expense = await ExpenseRepo.get_by_id(session, eid)

        card = await _render_expense_card(session, expense)
        return ExpenseResult(expense=expense, card_image=card)

    @staticmethod
    async def join_expense(
        session: AsyncSession,
        expense_id: int,
        user_id: int,
    ) -> ExpenseResult:
        """Добавить участника и пересчитать доли."""
        expense = await ExpenseRepo.get_by_id(session, expense_id)
        if expense is None:
            raise ValueError("Расход не найден")
        if expense.creator_id == user_id:
            raise ValueError("Создатель не может быть должником")

        # Добавить с временной долей 0
        added = await ExpenseRepo.add_participant(
            session, expense_id, user_id, amount=0
        )
        if not added:
            raise ValueError("Вы уже в списке должников")

        # Сбросить кэш identity map и перезагрузить с новым участником
        session.expire_all()
        expense = await ExpenseRepo.get_by_id(session, expense_id)

        # Пересчитать доли всех участников
        all_count = len(expense.participants)
        per_person, remainder = _recalculate_shares(expense.amount, all_count)

        amounts: dict[int, int] = {}
        unsettled = [p for p in expense.participants if not p.is_settled]
        for i, p in enumerate(unsettled):
            amounts[p.user_id] = per_person + (remainder if i == 0 else 0)

        await ExpenseRepo.update_participant_amounts(session, expense_id, amounts)

        # Сбросить кэш и перезагрузить с обновлёнными суммами
        session.expire_all()
        expense = await ExpenseRepo.get_by_id(session, expense_id)
        card = await _render_expense_card(session, expense)
        return ExpenseResult(expense=expense, card_image=card)

    @staticmethod
    async def settle_debt(
        session: AsyncSession,
        expense_id: int,
        user_id: int,
    ) -> ExpenseResult:
        """Отметить участника как отдавшего долг."""
        expense = await ExpenseRepo.get_by_id(session, expense_id)
        if expense is None:
            raise ValueError("Расход не найден")
        if expense.creator_id == user_id:
            raise ValueError("Создатель не может отметить оплату")

        settled = await ExpenseRepo.settle_participant(session, expense_id, user_id)
        if not settled:
            raise ValueError("Участник не найден или уже отметил оплату")

        session.expire_all()
        expense = await ExpenseRepo.get_by_id(session, expense_id)
        card = await _render_expense_card(session, expense)
        return ExpenseResult(expense=expense, card_image=card)
