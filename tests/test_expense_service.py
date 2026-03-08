from io import BytesIO

import pytest

from bot.db.repositories import UserRepo
from bot.services.expense_service import ExpenseService


pytestmark = pytest.mark.asyncio(loop_scope="function")


async def _create_user(
    session,
    telegram_id: int,
    first_name: str,
    username: str | None = None,
    bank: str = "sber",
    phone: str = "+79991234567",
) -> None:
    await UserRepo.upsert(session, telegram_id, first_name, username)
    await UserRepo.set_onboarded(session, telegram_id, phone, bank)


async def test_create_expense(db_session):
    """Создание расхода и начальная карточка."""
    await _create_user(db_session, 1, "Petya", "petya")

    result = await ExpenseService.create_expense(
        db_session, creator_id=1, amount=300000, description="за ужин"
    )
    assert result.expense.amount == 300000
    assert result.expense.description == "за ужин"
    assert result.expense.creator_id == 1
    assert isinstance(result.card_image, BytesIO)


async def test_join_expense_splits_equally(db_session):
    """1000₽ / 2 = 500₽ + 500₽."""
    await _create_user(db_session, 1, "Petya", "petya")
    await _create_user(db_session, 2, "Vasya", "vasya")
    await _create_user(db_session, 3, "Masha", "masha")

    result = await ExpenseService.create_expense(db_session, 1, 100000, "кофе")

    r = await ExpenseService.join_expense(db_session, result.expense.id, 2)
    assert len(r.expense.participants) == 1
    assert r.expense.participants[0].amount == 100000

    r = await ExpenseService.join_expense(db_session, result.expense.id, 3)
    amounts = sorted(p.amount for p in r.expense.participants)
    assert amounts == [50000, 50000]


async def test_join_expense_with_remainder(db_session):
    """100000 коп / 3 = 33334 + 33333 + 33333."""
    await _create_user(db_session, 1, "Petya", "petya")
    await _create_user(db_session, 2, "Vasya", "vasya")
    await _create_user(db_session, 3, "Masha", "masha")
    await _create_user(db_session, 4, "Kolya", "kolya")

    result = await ExpenseService.create_expense(db_session, 1, 100000, "ужин")
    await ExpenseService.join_expense(db_session, result.expense.id, 2)
    await ExpenseService.join_expense(db_session, result.expense.id, 3)
    r = await ExpenseService.join_expense(db_session, result.expense.id, 4)

    amounts = sorted(p.amount for p in r.expense.participants)
    assert amounts == [33333, 33333, 33334]
    assert sum(amounts) == 100000


async def test_join_multiple_recalculates(db_session):
    """Доли пересчитываются при каждом join."""
    await _create_user(db_session, 1, "Petya", "petya")
    await _create_user(db_session, 2, "Vasya", "vasya")
    await _create_user(db_session, 3, "Masha", "masha")

    result = await ExpenseService.create_expense(db_session, 1, 100000, "test")

    r1 = await ExpenseService.join_expense(db_session, result.expense.id, 2)
    assert r1.expense.participants[0].amount == 100000

    r2 = await ExpenseService.join_expense(db_session, result.expense.id, 3)
    for p in r2.expense.participants:
        assert p.amount == 50000


async def test_settle_debt(db_session):
    """Отметка погашения долга."""
    await _create_user(db_session, 1, "Petya", "petya")
    await _create_user(db_session, 2, "Vasya", "vasya")

    result = await ExpenseService.create_expense(db_session, 1, 100000, "test")
    await ExpenseService.join_expense(db_session, result.expense.id, 2)

    r = await ExpenseService.settle_debt(db_session, result.expense.id, 2)
    settled = [p for p in r.expense.participants if p.is_settled]
    assert len(settled) == 1
    assert settled[0].user_id == 2
    assert isinstance(r.card_image, BytesIO)


async def test_settle_debt_duplicate(db_session):
    """Повторный settle — ошибка."""
    await _create_user(db_session, 1, "Petya", "petya")
    await _create_user(db_session, 2, "Vasya", "vasya")

    result = await ExpenseService.create_expense(db_session, 1, 100000, "test")
    await ExpenseService.join_expense(db_session, result.expense.id, 2)
    await ExpenseService.settle_debt(db_session, result.expense.id, 2)

    with pytest.raises(ValueError):
        await ExpenseService.settle_debt(db_session, result.expense.id, 2)


async def test_join_creator_cannot(db_session):
    """Создатель не может быть должником."""
    await _create_user(db_session, 1, "Petya", "petya")

    result = await ExpenseService.create_expense(db_session, 1, 100000, "test")
    with pytest.raises(ValueError, match="Создатель"):
        await ExpenseService.join_expense(db_session, result.expense.id, 1)


async def test_settle_creator_cannot(db_session):
    """Создатель не может отметить оплату."""
    await _create_user(db_session, 1, "Petya", "petya")

    result = await ExpenseService.create_expense(db_session, 1, 100000, "test")
    with pytest.raises(ValueError, match="Создатель"):
        await ExpenseService.settle_debt(db_session, result.expense.id, 1)


async def test_validate_amount_min_max(db_session):
    """Проверка границ суммы: 1₽ — 1 000 000₽."""
    await _create_user(db_session, 1, "Petya", "petya")

    with pytest.raises(ValueError):
        await ExpenseService.create_expense(db_session, 1, 99, "слишком мало")

    with pytest.raises(ValueError):
        await ExpenseService.create_expense(db_session, 1, 100_000_001, "слишком много")

    # Граничные значения — валидны
    r_min = await ExpenseService.create_expense(db_session, 1, 100, "минимум")
    assert r_min.expense.amount == 100

    r_max = await ExpenseService.create_expense(db_session, 1, 100_000_000, "максимум")
    assert r_max.expense.amount == 100_000_000
