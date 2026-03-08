import pytest

from bot.db.repositories import ExpenseRepo, UserRepo


pytestmark = pytest.mark.asyncio(loop_scope="function")


# --- UserRepo ---


async def test_user_upsert_creates_new(db_session):
    user = await UserRepo.upsert(
        db_session, telegram_id=1, first_name="Alice", username="alice"
    )
    assert user.telegram_id == 1
    assert user.first_name == "Alice"


async def test_user_upsert_updates_existing(db_session):
    await UserRepo.upsert(
        db_session, telegram_id=1, first_name="Alice", username="alice"
    )
    user = await UserRepo.upsert(
        db_session, telegram_id=1, first_name="Alice2", username="alice_new"
    )
    assert user.first_name == "Alice2"
    assert user.username == "alice_new"


async def test_user_set_onboarded(db_session):
    await UserRepo.upsert(db_session, telegram_id=1, first_name="Alice")
    user = await UserRepo.set_onboarded(
        db_session, telegram_id=1, phone="+79991234567", bank_name="sber"
    )
    assert user.is_onboarded is True
    assert user.phone == "+79991234567"


# --- ExpenseRepo ---


async def _create_users(db_session):
    """Хелпер: создать 3 пользователей для тестов."""
    await UserRepo.upsert(
        db_session, telegram_id=1, first_name="Петя", username="petya"
    )
    await UserRepo.upsert(
        db_session, telegram_id=2, first_name="Вася", username="vasya"
    )
    await UserRepo.upsert(
        db_session, telegram_id=3, first_name="Маша", username="masha"
    )


async def test_expense_create(db_session):
    await _create_users(db_session)
    expense = await ExpenseRepo.create(
        db_session, creator_id=1, amount=300000, description="за ужин"
    )
    assert expense.id is not None
    assert expense.amount == 300000
    assert expense.description == "за ужин"
    assert expense.creator_id == 1


async def test_expense_get_by_id(db_session):
    await _create_users(db_session)
    expense = await ExpenseRepo.create(
        db_session, creator_id=1, amount=100000, description="кофе"
    )
    fetched = await ExpenseRepo.get_by_id(db_session, expense.id)
    assert fetched is not None
    assert fetched.amount == 100000


async def test_expense_get_by_id_not_found(db_session):
    result = await ExpenseRepo.get_by_id(db_session, 999)
    assert result is None


async def test_expense_set_inline_message_id(db_session):
    await _create_users(db_session)
    expense = await ExpenseRepo.create(
        db_session, creator_id=1, amount=50000, description="тест"
    )
    await ExpenseRepo.set_inline_message_id(db_session, expense.id, "msg_123")
    fetched = await ExpenseRepo.get_by_id(db_session, expense.id)
    assert fetched.inline_message_id == "msg_123"


async def test_expense_set_card_file_id(db_session):
    await _create_users(db_session)
    expense = await ExpenseRepo.create(
        db_session, creator_id=1, amount=50000, description="тест"
    )
    await ExpenseRepo.set_card_file_id(db_session, expense.id, "file_abc")
    fetched = await ExpenseRepo.get_by_id(db_session, expense.id)
    assert fetched.card_file_id == "file_abc"


async def test_expense_add_participant(db_session):
    await _create_users(db_session)
    expense = await ExpenseRepo.create(
        db_session, creator_id=1, amount=300000, description="ужин"
    )
    added = await ExpenseRepo.add_participant(
        db_session, expense_id=expense.id, user_id=2, amount=150000
    )
    assert added is True

    fetched = await ExpenseRepo.get_by_id(db_session, expense.id)
    assert len(fetched.participants) == 1
    assert fetched.participants[0].user_id == 2
    assert fetched.participants[0].amount == 150000


async def test_expense_add_participant_duplicate(db_session):
    await _create_users(db_session)
    expense = await ExpenseRepo.create(
        db_session, creator_id=1, amount=300000, description="ужин"
    )
    await ExpenseRepo.add_participant(
        db_session, expense_id=expense.id, user_id=2, amount=150000
    )
    duplicate = await ExpenseRepo.add_participant(
        db_session, expense_id=expense.id, user_id=2, amount=150000
    )
    assert duplicate is False


async def test_expense_settle_participant(db_session):
    await _create_users(db_session)
    expense = await ExpenseRepo.create(
        db_session, creator_id=1, amount=300000, description="ужин"
    )
    await ExpenseRepo.add_participant(
        db_session, expense_id=expense.id, user_id=2, amount=150000
    )
    settled = await ExpenseRepo.settle_participant(
        db_session, expense_id=expense.id, user_id=2
    )
    assert settled is True

    fetched = await ExpenseRepo.get_by_id(db_session, expense.id)
    assert fetched.participants[0].is_settled is True
    assert fetched.participants[0].settled_at is not None


async def test_expense_settle_participant_already_settled(db_session):
    await _create_users(db_session)
    expense = await ExpenseRepo.create(
        db_session, creator_id=1, amount=300000, description="ужин"
    )
    await ExpenseRepo.add_participant(
        db_session, expense_id=expense.id, user_id=2, amount=150000
    )
    await ExpenseRepo.settle_participant(db_session, expense_id=expense.id, user_id=2)
    # Повторная отметка — False
    result = await ExpenseRepo.settle_participant(
        db_session, expense_id=expense.id, user_id=2
    )
    assert result is False


async def test_expense_update_participant_amounts(db_session):
    await _create_users(db_session)
    expense = await ExpenseRepo.create(
        db_session, creator_id=1, amount=300000, description="ужин"
    )
    await ExpenseRepo.add_participant(
        db_session, expense_id=expense.id, user_id=2, amount=300000
    )
    await ExpenseRepo.add_participant(
        db_session, expense_id=expense.id, user_id=3, amount=300000
    )
    # Обновляем доли: {2: 150000, 3: 150000}
    await ExpenseRepo.update_participant_amounts(
        db_session, expense_id=expense.id, amounts={2: 150000, 3: 150000}
    )
    fetched = await ExpenseRepo.get_by_id(db_session, expense.id)
    amounts = {p.user_id: p.amount for p in fetched.participants}
    assert amounts == {2: 150000, 3: 150000}
