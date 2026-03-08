from __future__ import annotations

from aiogram import Bot, Router
from aiogram.types import (
    CallbackQuery,
    InputMediaPhoto,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot.callback_data import ExpenseCallback
from bot.db.repositories import UserRepo
from bot.keyboards import expense_keyboard
from bot.services.expense_service import ExpenseService
from bot.upload import upload_photo

router = Router()


@router.callback_query(ExpenseCallback.filter())
async def on_expense_callback(
    callback: CallbackQuery,
    callback_data: ExpenseCallback,
    bot: Bot,
    session: AsyncSession,
) -> None:
    """Обработка кнопок 'Я должен' и 'Я отдал'."""
    expense_id = callback_data.expense_id
    action = callback_data.action
    user_id = callback.from_user.id

    # Upsert пользователя
    await UserRepo.upsert(
        session,
        telegram_id=user_id,
        first_name=callback.from_user.first_name,
        username=callback.from_user.username,
    )

    # Выполнить действие
    if action == "join":
        try:
            result = await ExpenseService.join_expense(session, expense_id, user_id)
        except ValueError as e:
            await callback.answer(str(e), show_alert=True)
            return
        await callback.answer("Вы добавлены в список должников")

    elif action == "settle":
        try:
            result = await ExpenseService.settle_debt(session, expense_id, user_id)
        except ValueError as e:
            await callback.answer(str(e), show_alert=True)
            return
        await callback.answer("Оплата отмечена ✓")

    else:
        await callback.answer("Неизвестное действие", show_alert=True)
        return

    # Загрузить карточку → file_id (через канал или ЛС создателя)
    file_id = await upload_photo(
        bot, result.card_image.read(), result.expense.creator_id
    )

    # Сохранить file_id
    await ExpenseService.set_card_file_id(session, expense_id, file_id)

    # Обновить inline-сообщение
    if callback.inline_message_id:
        await bot.edit_message_media(
            inline_message_id=callback.inline_message_id,
            media=InputMediaPhoto(media=file_id),
            reply_markup=expense_keyboard(expense_id),
        )
