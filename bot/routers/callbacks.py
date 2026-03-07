from aiogram import Bot, Router
from aiogram.types import BufferedInputFile, CallbackQuery, InputMediaPhoto
from sqlalchemy.ext.asyncio import AsyncSession

from bot.callback_data import PaymentCallback
from bot.db.repositories import UserRepo
from bot.services.payment import PaymentService

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
        photo = BufferedInputFile(result.card_bytes.read(), filename="card.png")
        keyboard = callback.message.reply_markup if callback.message else None

        await bot.edit_message_media(
            inline_message_id=callback.inline_message_id,
            media=InputMediaPhoto(media=photo),
            reply_markup=keyboard,
        )

    await callback.answer("Оплата отмечена ✓")
