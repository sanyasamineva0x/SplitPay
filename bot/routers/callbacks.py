from __future__ import annotations

from aiogram import Bot, Router
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot.callback_data import ExpenseCallback
from bot.db.repositories import ExpenseRepo, UserRepo
from bot.services.expense_service import ExpenseService

router = Router()


def expense_keyboard(expense_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для карточки расхода."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Я должен 💰",
                    callback_data=ExpenseCallback(
                        expense_id=expense_id, action="join"
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="Я отдал ✓",
                    callback_data=ExpenseCallback(
                        expense_id=expense_id, action="settle"
                    ).pack(),
                ),
            ]
        ]
    )


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

    # Workaround: отправить фото в ЛС → file_id → удалить → edit inline
    photo_msg = await bot.send_photo(
        chat_id=user_id,
        photo=BufferedInputFile(result.card_image.read(), filename="card.png"),
    )
    file_id = photo_msg.photo[-1].file_id
    await bot.delete_message(chat_id=user_id, message_id=photo_msg.message_id)

    # Сохранить file_id
    await ExpenseRepo.set_card_file_id(session, expense_id, file_id)

    # Обновить inline-сообщение
    if callback.inline_message_id:
        await bot.edit_message_media(
            inline_message_id=callback.inline_message_id,
            media=InputMediaPhoto(media=file_id),
            reply_markup=expense_keyboard(expense_id),
        )
