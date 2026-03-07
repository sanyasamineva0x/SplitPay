import logging
import re

from aiogram import Bot, Router
from aiogram.types import (
    BufferedInputFile,
    ChosenInlineResult,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultPhoto,
    InlineQueryResultsButton,
    InputMediaPhoto,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot.callback_data import PaymentCallback
from bot.db.repositories import PaymentRepo, UserRepo
from bot.services.payment import PaymentService

logger = logging.getLogger(__name__)

router = Router()

PLACEHOLDER_URL = (
    "https://raw.githubusercontent.com/sanyasamineva0x/TGpay/main/assets/placeholder.png"
)
QUERY_RE = re.compile(r"^(\d+)\s*(.*)?$")


def _parse_query(text: str) -> tuple[int, str] | None:
    m = QUERY_RE.match(text.strip())
    if not m:
        return None
    amount_rubles = int(m.group(1))
    description = (m.group(2) or "").strip() or "Оплата"
    return amount_rubles * 100, description


@router.inline_query()
async def on_inline_query(inline_query: InlineQuery, session: AsyncSession) -> None:
    user = await UserRepo.get_by_id(session, inline_query.from_user.id)

    if not user or not user.is_onboarded:
        await inline_query.answer(
            results=[],
            button=InlineQueryResultsButton(
                text="Сначала настрой бота →",
                start_parameter="onboarding",
            ),
            cache_time=5,
            is_personal=True,
        )
        return

    parsed = _parse_query(inline_query.query)
    if not parsed:
        await inline_query.answer(results=[], cache_time=5, is_personal=True)
        return

    amount, description = parsed
    amount_text = f"{amount // 100} ₽"

    results = [
        InlineQueryResultPhoto(
            id=f"{inline_query.from_user.id}:{amount}:{description}",
            photo_url=PLACEHOLDER_URL,
            thumbnail_url=PLACEHOLDER_URL,
            title=f"Запросить {amount_text}",
            description=description,
            photo_width=600,
            photo_height=400,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Загрузка...", callback_data="loading")]
                ]
            ),
        )
    ]

    await inline_query.answer(results=results, cache_time=5, is_personal=True)


@router.chosen_inline_result()
async def on_chosen_result(
    chosen: ChosenInlineResult, bot: Bot, session: AsyncSession
) -> None:
    logger.info("chosen_inline_result: query=%s, inline_message_id=%s",
                chosen.query, chosen.inline_message_id)
    try:
        parsed = _parse_query(chosen.query)
        if not parsed:
            logger.warning("chosen_inline_result: не удалось распарсить query")
            return

        amount, description = parsed

        payment, card_bytes = await PaymentService.create_payment(
            session=session,
            creator_id=chosen.from_user.id,
            amount=amount,
            description=description,
        )
        logger.info("Платёж #%d создан", payment.id)

        if chosen.inline_message_id:
            await PaymentRepo.set_inline_message_id(
                session, payment.id, chosen.inline_message_id
            )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Я оплатил ✓",
                        callback_data=PaymentCallback(
                            payment_id=payment.id, action="paid"
                        ).pack(),
                    ),
                ]
            ]
        )

        if chosen.inline_message_id:
            # Для inline-сообщений нельзя загружать файлы напрямую —
            # нужен file_id. Отправляем фото в личку, берём file_id, удаляем.
            photo = BufferedInputFile(card_bytes.read(), filename="card.png")
            tmp_msg = await bot.send_photo(
                chat_id=chosen.from_user.id,
                photo=photo,
                disable_notification=True,
            )
            file_id = tmp_msg.photo[-1].file_id
            await bot.delete_message(
                chat_id=chosen.from_user.id, message_id=tmp_msg.message_id
            )

            await bot.edit_message_media(
                inline_message_id=chosen.inline_message_id,
                media=InputMediaPhoto(media=file_id),
                reply_markup=keyboard,
            )
            logger.info("Карточка отправлена для inline_message_id=%s",
                        chosen.inline_message_id)
        else:
            logger.warning("inline_message_id отсутствует!")
    except Exception:
        logger.exception("Ошибка в on_chosen_result")
