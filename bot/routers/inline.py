from __future__ import annotations

import logging
import re

from aiogram import Bot, Router
from aiogram.types import (
    ChosenInlineResult,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultCachedPhoto,
    InputMediaPhoto,
    InputTextMessageContent,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.db.repositories import UserRepo
from bot.keyboards import expense_keyboard
from bot.services.card_renderer import render_placeholder
from bot.services.expense_service import ExpenseService
from bot.upload import upload_photo

logger = logging.getLogger(__name__)

router = Router()

# Парсинг: целые и дробные суммы (точка/запятая), 1-2 знака после
_QUERY_RE = re.compile(r"^(\d+(?:[.,]\d{1,2})?)\s+(.+)$")

# Кэш file_id placeholder-карточки (загружается лениво при первом запросе)
_placeholder_file_id: str | None = None


def parse_inline_query(text: str) -> tuple[int, str] | None:
    """Парсинг inline query: '3000 за ужин' → (300000, 'за ужин').

    Возвращает (amount_kopecks, description) или None если невалидно.
    """
    text = text.strip()
    m = _QUERY_RE.match(text)
    if not m:
        return None

    amount_str = m.group(1).replace(",", ".")
    description = m.group(2).strip()

    try:
        amount_float = float(amount_str)
    except ValueError:
        return None

    amount_kopecks = round(amount_float * 100)
    if amount_kopecks < 100 or amount_kopecks > 100_000_000:
        return None

    if not (1 <= len(description) <= 100):
        return None

    return amount_kopecks, description


def _format_amount(kopecks: int) -> str:
    """Форматирование суммы для текста (не для карточки)."""
    rubles = kopecks // 100
    kop = kopecks % 100
    if kop:
        return f"{rubles},{kop:02d} ₽"
    return f"{rubles:,} ₽".replace(",", " ")


async def _get_placeholder_file_id(bot: Bot, chat_id: int) -> str:
    """Получить file_id placeholder-карточки (лениво загружает при первом вызове)."""
    global _placeholder_file_id  # noqa: PLW0603
    if _placeholder_file_id is not None:
        return _placeholder_file_id

    placeholder = render_placeholder()
    file_id = await upload_photo(bot, placeholder.read(), chat_id)
    _placeholder_file_id = file_id
    return file_id


@router.inline_query()
async def on_inline_query(
    inline_query: InlineQuery,
    bot: Bot,
    session: AsyncSession,
) -> None:
    """Обработка inline query: парсинг суммы и описания."""
    user = await UserRepo.get_by_id(session, inline_query.from_user.id)
    me = await bot.get_me()
    bot_username = f"@{me.username}"

    if not user or not user.is_onboarded:
        await inline_query.answer(
            results=[
                InlineQueryResultArticle(
                    id="not_onboarded",
                    title="Сначала настройте бота",
                    description=f"Напишите /start в ЛС {bot_username}",
                    input_message_content=InputTextMessageContent(
                        message_text=f"Напишите /start боту {bot_username}",
                    ),
                )
            ],
            cache_time=5,
            is_personal=True,
        )
        return

    parsed = parse_inline_query(inline_query.query)
    if parsed is None:
        await inline_query.answer(
            results=[
                InlineQueryResultArticle(
                    id="hint",
                    title="Формат: сумма описание",
                    description="Пример: 3000 за ужин",
                    input_message_content=InputTextMessageContent(
                        message_text=f"Формат: {bot_username} [сумма] [описание]\n"
                        f"Пример: {bot_username} 3000 за ужин",
                    ),
                )
            ],
            cache_time=5,
            is_personal=True,
        )
        return

    amount, description = parsed

    # Получить file_id placeholder-а (лениво загружается при первом вызове)
    settings = get_settings()
    upload_target = settings.upload_chat_id or inline_query.from_user.id
    try:
        placeholder_fid = await _get_placeholder_file_id(bot, upload_target)
    except Exception:
        logger.exception("Не удалось загрузить placeholder")
        # Fallback — текстовый результат (edit_message_media не сработает,
        # но хотя бы inline query не сломается)
        await inline_query.answer(
            results=[
                InlineQueryResultArticle(
                    id="expense",
                    title=f"{_format_amount(amount)} — {description}",
                    description="Нажмите, чтобы отправить в чат",
                    input_message_content=InputTextMessageContent(
                        message_text=f"💰 {_format_amount(amount)} — {description}\n\n"
                        "Загрузка карточки...",
                    ),
                )
            ],
            cache_time=5,
            is_personal=True,
        )
        return

    # Отправляем фото-placeholder с кнопкой-заглушкой.
    # reply_markup ОБЯЗАТЕЛЕН — без него Telegram не пришлёт inline_message_id
    # в chosen_inline_result, и edit_message_media будет невозможен.
    loading_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏳ Загрузка...", callback_data="noop")]
        ]
    )
    await inline_query.answer(
        results=[
            InlineQueryResultCachedPhoto(
                id="expense",
                photo_file_id=placeholder_fid,
                title=f"{_format_amount(amount)} — {description}",
                description="Нажмите, чтобы отправить в чат",
                caption=f"💰 {_format_amount(amount)} — {description}\n\n"
                "Загрузка карточки...",
                reply_markup=loading_keyboard,
            )
        ],
        cache_time=5,
        is_personal=True,
    )


@router.chosen_inline_result()
async def on_chosen_inline_result(
    chosen: ChosenInlineResult,
    bot: Bot,
    session: AsyncSession,
) -> None:
    """Создание расхода после выбора inline результата."""
    parsed = parse_inline_query(chosen.query)
    if parsed is None:
        return

    amount, description = parsed
    creator_id = chosen.from_user.id

    # Upsert пользователя
    await UserRepo.upsert(
        session,
        telegram_id=creator_id,
        first_name=chosen.from_user.first_name,
        username=chosen.from_user.username,
    )

    # Создать расход
    result = await ExpenseService.create_expense(
        session, creator_id, amount, description
    )
    expense = result.expense

    # Сохранить inline_message_id
    if chosen.inline_message_id:
        await ExpenseService.set_inline_message_id(
            session, expense.id, chosen.inline_message_id
        )

    # Загрузить карточку → file_id (через канал или ЛС создателя)
    file_id = await upload_photo(bot, result.card_image.read(), creator_id)

    # Сохранить file_id
    await ExpenseService.set_card_file_id(session, expense.id, file_id)

    # Обновить inline-сообщение: placeholder → карточка + кнопки
    if chosen.inline_message_id:
        await bot.edit_message_media(
            inline_message_id=chosen.inline_message_id,
            media=InputMediaPhoto(media=file_id),
            reply_markup=expense_keyboard(expense.id),
        )
