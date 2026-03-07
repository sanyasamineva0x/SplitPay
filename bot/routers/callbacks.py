import logging

from aiogram import Bot, Router
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot.callback_data import PaymentCallback
from bot.db.repositories import UserRepo
from bot.services.payment import PaymentService

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(PaymentCallback.filter())
async def on_payment_callback(
    callback: CallbackQuery,
    callback_data: PaymentCallback,
    bot: Bot,
    session: AsyncSession,
) -> None:
    if callback_data.action != "paid":
        await callback.answer()
        return

    await UserRepo.upsert(
        session,
        telegram_id=callback.from_user.id,
        first_name=callback.from_user.first_name,
        username=callback.from_user.username,
    )

    result = await PaymentService.mark_paid(
        session=session,
        payment_id=callback_data.payment_id,
        user_id=callback.from_user.id,
    )

    if not result.added:
        await callback.answer("Ты уже отметился!")
        return

    if result.card_bytes and callback.inline_message_id:
        try:
            # Для inline-сообщений нельзя загружать файлы —
            # отправляем в личку, берём file_id, удаляем.
            photo = BufferedInputFile(result.card_bytes.read(), filename="card.png")
            tmp_msg = await bot.send_photo(
                chat_id=callback.from_user.id,
                photo=photo,
                disable_notification=True,
            )
            file_id = tmp_msg.photo[-1].file_id
            await bot.delete_message(
                chat_id=callback.from_user.id, message_id=tmp_msg.message_id
            )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Я оплатил ✓",
                            callback_data=PaymentCallback(
                                payment_id=callback_data.payment_id, action="paid"
                            ).pack(),
                        ),
                    ]
                ]
            )

            await bot.edit_message_media(
                inline_message_id=callback.inline_message_id,
                media=InputMediaPhoto(media=file_id),
                reply_markup=keyboard,
            )
        except Exception:
            logger.exception("Ошибка обновления карточки")

    await callback.answer("Оплата отмечена ✓")
