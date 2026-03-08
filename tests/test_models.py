import pytest
from sqlalchemy import select

from bot.db.models import Expense, ExpenseParticipant, User


pytestmark = pytest.mark.asyncio(loop_scope="function")


async def test_create_user(db_session):
    user = User(telegram_id=123, first_name="Alice", username="alice")
    db_session.add(user)
    await db_session.commit()

    result = await db_session.execute(select(User).where(User.telegram_id == 123))
    saved = result.scalar_one()
    assert saved.first_name == "Alice"
    assert saved.is_onboarded is False


async def test_create_expense(db_session):
    creator = User(telegram_id=1, first_name="Петя")
    db_session.add(creator)
    await db_session.flush()

    expense = Expense(creator_id=1, amount=300000, description="за ужин")
    db_session.add(expense)
    await db_session.commit()

    result = await db_session.execute(select(Expense).where(Expense.id == expense.id))
    saved = result.scalar_one()
    assert saved.amount == 300000
    assert saved.description == "за ужин"
    assert saved.creator_id == 1
    assert saved.inline_message_id is None
    assert saved.card_file_id is None


async def test_create_expense_with_participants(db_session):
    creator = User(telegram_id=1, first_name="Петя")
    vasya = User(telegram_id=2, first_name="Вася")
    masha = User(telegram_id=3, first_name="Маша")
    db_session.add_all([creator, vasya, masha])
    await db_session.flush()

    expense = Expense(creator_id=1, amount=300000, description="за ужин")
    db_session.add(expense)
    await db_session.flush()

    p1 = ExpenseParticipant(
        expense_id=expense.id, user_id=2, amount=150000, is_settled=False
    )
    p2 = ExpenseParticipant(
        expense_id=expense.id, user_id=3, amount=150000, is_settled=False
    )
    db_session.add_all([p1, p2])
    await db_session.commit()

    result = await db_session.execute(select(Expense).where(Expense.id == expense.id))
    saved = result.scalar_one()
    assert len(saved.participants) == 2
    assert saved.participants[0].amount == 150000
    assert saved.participants[0].is_settled is False
    assert saved.participants[0].settled_at is None


async def test_expense_participant_settled(db_session):
    creator = User(telegram_id=1, first_name="Петя")
    vasya = User(telegram_id=2, first_name="Вася")
    db_session.add_all([creator, vasya])
    await db_session.flush()

    expense = Expense(creator_id=1, amount=100000, description="кофе")
    db_session.add(expense)
    await db_session.flush()

    p = ExpenseParticipant(
        expense_id=expense.id, user_id=2, amount=100000, is_settled=True
    )
    db_session.add(p)
    await db_session.commit()

    result = await db_session.execute(select(Expense).where(Expense.id == expense.id))
    saved = result.scalar_one()
    assert saved.participants[0].is_settled is True
