from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.callback_data import ExpenseCallback
from bot.db.repositories import UserRepo
from bot.routers.callbacks import on_expense_callback
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


def _make_callback(
    user_id: int,
    first_name: str,
    username: str | None,
    inline_message_id: str = "inline_123",
) -> AsyncMock:
    """Создать мок CallbackQuery."""
    callback = AsyncMock()
    callback.from_user = MagicMock()
    callback.from_user.id = user_id
    callback.from_user.first_name = first_name
    callback.from_user.username = username
    callback.inline_message_id = inline_message_id
    return callback


def _make_bot() -> AsyncMock:
    """Создать мок Bot с поддержкой send_photo → file_id."""
    bot = AsyncMock()
    photo_msg = MagicMock()
    photo_msg.photo = [MagicMock(file_id="test_file_id")]
    photo_msg.message_id = 999
    bot.send_photo.return_value = photo_msg
    return bot


async def test_callback_join_success(db_session):
    """Join добавляет участника и обновляет карточку."""
    await _create_user(db_session, 1, "Petya", "petya")
    await _create_user(db_session, 2, "Vasya", "vasya")

    result = await ExpenseService.create_expense(db_session, 1, 100000, "ужин")
    callback_data = ExpenseCallback(expense_id=result.expense.id, action="join")
    callback = _make_callback(2, "Vasya", "vasya")
    bot = _make_bot()

    await on_expense_callback(callback, callback_data, bot, db_session)

    # answer вызван без show_alert (успех)
    callback.answer.assert_called_once()
    assert not callback.answer.call_args.kwargs.get("show_alert", False)
    # Карточка обновлена
    bot.edit_message_media.assert_called_once()


async def test_callback_join_creator_rejected(db_session):
    """Создатель не может join свой расход."""
    await _create_user(db_session, 1, "Petya", "petya")

    result = await ExpenseService.create_expense(db_session, 1, 100000, "ужин")
    callback_data = ExpenseCallback(expense_id=result.expense.id, action="join")
    callback = _make_callback(1, "Petya", "petya")
    bot = _make_bot()

    await on_expense_callback(callback, callback_data, bot, db_session)

    callback.answer.assert_called_once()
    assert callback.answer.call_args.kwargs.get("show_alert") is True
    assert "Создатель" in callback.answer.call_args.args[0]
    # Карточка НЕ обновлена
    bot.edit_message_media.assert_not_called()


async def test_callback_join_duplicate_rejected(db_session):
    """Повторный join отклоняется."""
    await _create_user(db_session, 1, "Petya", "petya")
    await _create_user(db_session, 2, "Vasya", "vasya")

    result = await ExpenseService.create_expense(db_session, 1, 100000, "ужин")

    # Первый join
    cb1 = _make_callback(2, "Vasya", "vasya")
    bot1 = _make_bot()
    cb_data = ExpenseCallback(expense_id=result.expense.id, action="join")
    await on_expense_callback(cb1, cb_data, bot1, db_session)

    # Повторный join
    cb2 = _make_callback(2, "Vasya", "vasya")
    bot2 = _make_bot()
    await on_expense_callback(cb2, cb_data, bot2, db_session)

    assert cb2.answer.call_args.kwargs.get("show_alert") is True
    assert "уже" in cb2.answer.call_args.args[0]


async def test_callback_settle_success(db_session):
    """Settle отмечает оплату."""
    await _create_user(db_session, 1, "Petya", "petya")
    await _create_user(db_session, 2, "Vasya", "vasya")

    result = await ExpenseService.create_expense(db_session, 1, 100000, "ужин")

    # Сначала join
    cb_join = _make_callback(2, "Vasya", "vasya")
    bot_join = _make_bot()
    await on_expense_callback(
        cb_join,
        ExpenseCallback(expense_id=result.expense.id, action="join"),
        bot_join,
        db_session,
    )

    # Затем settle
    cb_settle = _make_callback(2, "Vasya", "vasya")
    bot_settle = _make_bot()
    await on_expense_callback(
        cb_settle,
        ExpenseCallback(expense_id=result.expense.id, action="settle"),
        bot_settle,
        db_session,
    )

    cb_settle.answer.assert_called_once()
    assert not cb_settle.answer.call_args.kwargs.get("show_alert", False)
    bot_settle.edit_message_media.assert_called_once()


async def test_callback_settle_not_participant(db_session):
    """Settle для не-участника отклоняется."""
    await _create_user(db_session, 1, "Petya", "petya")
    await _create_user(db_session, 2, "Vasya", "vasya")

    result = await ExpenseService.create_expense(db_session, 1, 100000, "ужин")
    callback_data = ExpenseCallback(expense_id=result.expense.id, action="settle")
    callback = _make_callback(2, "Vasya", "vasya")
    bot = _make_bot()

    await on_expense_callback(callback, callback_data, bot, db_session)

    callback.answer.assert_called_once()
    assert callback.answer.call_args.kwargs.get("show_alert") is True
    bot.edit_message_media.assert_not_called()
