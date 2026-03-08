from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Expense, ExpenseParticipant, User


class UserRepo:
    @staticmethod
    async def upsert(
        session: AsyncSession,
        telegram_id: int,
        first_name: str,
        username: str | None = None,
    ) -> User:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=telegram_id, first_name=first_name, username=username
            )
            session.add(user)
        else:
            user.first_name = first_name
            user.username = username
        await session.commit()
        return user

    @staticmethod
    async def get_by_id(session: AsyncSession, telegram_id: int) -> User | None:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_ids(session: AsyncSession, telegram_ids: list[int]) -> list[User]:
        """Загрузить пользователей по списку ID одним запросом."""
        if not telegram_ids:
            return []
        result = await session.execute(
            select(User).where(User.telegram_id.in_(telegram_ids))
        )
        return list(result.scalars().all())

    @staticmethod
    async def set_onboarded(
        session: AsyncSession,
        telegram_id: int,
        phone: str,
        bank_name: str,
    ) -> User:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one()
        user.phone = phone
        user.bank_name = bank_name
        user.is_onboarded = True
        await session.commit()
        return user


class ExpenseRepo:
    @staticmethod
    async def create(
        session: AsyncSession,
        creator_id: int,
        amount: int,
        description: str,
    ) -> Expense:
        expense = Expense(creator_id=creator_id, amount=amount, description=description)
        session.add(expense)
        await session.commit()
        return expense

    @staticmethod
    async def get_by_id(session: AsyncSession, expense_id: int) -> Expense | None:
        result = await session.execute(select(Expense).where(Expense.id == expense_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def set_inline_message_id(
        session: AsyncSession,
        expense_id: int,
        inline_message_id: str,
    ) -> None:
        result = await session.execute(select(Expense).where(Expense.id == expense_id))
        expense = result.scalar_one()
        expense.inline_message_id = inline_message_id
        await session.commit()

    @staticmethod
    async def set_card_file_id(
        session: AsyncSession,
        expense_id: int,
        card_file_id: str,
    ) -> None:
        result = await session.execute(select(Expense).where(Expense.id == expense_id))
        expense = result.scalar_one()
        expense.card_file_id = card_file_id
        await session.commit()

    @staticmethod
    async def add_participant(
        session: AsyncSession,
        expense_id: int,
        user_id: int,
        amount: int,
    ) -> bool:
        """Добавить участника. Возвращает False если дубликат."""
        participant = ExpenseParticipant(
            expense_id=expense_id, user_id=user_id, amount=amount
        )
        session.add(participant)
        try:
            await session.commit()
            return True
        except IntegrityError:
            await session.rollback()
            return False

    @staticmethod
    async def settle_participant(
        session: AsyncSession,
        expense_id: int,
        user_id: int,
    ) -> bool:
        """Отметить участника как отдавшего. Возвращает False если уже settled."""
        result = await session.execute(
            select(ExpenseParticipant).where(
                ExpenseParticipant.expense_id == expense_id,
                ExpenseParticipant.user_id == user_id,
            )
        )
        participant = result.scalar_one_or_none()
        if participant is None or participant.is_settled:
            return False
        participant.is_settled = True
        participant.settled_at = datetime.now(timezone.utc)
        await session.commit()
        return True

    @staticmethod
    async def update_participant_amounts(
        session: AsyncSession,
        expense_id: int,
        amounts: dict[int, int],
    ) -> None:
        """Обновить доли всех участников. amounts: {user_id: amount_kopecks}."""
        result = await session.execute(
            select(ExpenseParticipant).where(
                ExpenseParticipant.expense_id == expense_id
            )
        )
        for participant in result.scalars().all():
            if participant.user_id in amounts:
                participant.amount = amounts[participant.user_id]
        await session.commit()
