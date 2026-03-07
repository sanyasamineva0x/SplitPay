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
        )
    ]

    await inline_query.answer(results=results, cache_time=5, is_personal=True)


@router.chosen_inline_result()
async def on_chosen_result(
    chosen: ChosenInlineResult, bot: Bot, session: AsyncSession
) -> None:
    parsed = _parse_query(chosen.query)
    if not parsed:
        return

    amount, description = parsed

    payment, card_bytes = await PaymentService.create_payment(
        session=session,
        creator_id=chosen.from_user.id,
        amount=amount,
        description=description,
    )

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

    photo = BufferedInputFile(card_bytes.read(), filename="card.png")

    if chosen.inline_message_id:
        await bot.edit_message_media(
            inline_message_id=chosen.inline_message_id,
            media=InputMediaPhoto(media=photo),
            reply_markup=keyboard,
        )
