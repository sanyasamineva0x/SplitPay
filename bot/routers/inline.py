from __future__ import annotations

import re

from aiogram import Bot, Router
from aiogram.types import (
    BufferedInputFile,
    ChosenInlineResult,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputMediaPhoto,
    InputTextMessageContent,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot.callback_data import ExpenseCallback
from bot.db.repositories import ExpenseRepo, UserRepo
from bot.services.expense_service import ExpenseService

router = Router()

# Парсинг: целые и дробные суммы (точка/запятая), 1-2 знака после
_QUERY_RE = re.compile(r"^(\d+(?:[.,]\d{1,2})?)\s+(.+)$")


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


def expense_keyboard(expense_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с кнопками 'Я должен' и 'Я отдал'."""
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


@router.inline_query()
async def on_inline_query(
    inline_query: InlineQuery,
    session: AsyncSession,
) -> None:
    """Обработка inline query: парсинг суммы и описания."""
    user = await UserRepo.get_by_id(session, inline_query.from_user.id)

    if not user or not user.is_onboarded:
        await inline_query.answer(
            results=[
                InlineQueryResultArticle(
                    id="not_onboarded",
                    title="Сначала настройте бота",
                    description="Напишите /start в ЛС @SplitPayBot",
                    input_message_content=InputTextMessageContent(
                        message_text="Напишите /start боту @SplitPayBot",
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
                        message_text="Формат: @SplitPayBot <сумма> <описание>\n"
                        "Пример: @SplitPayBot 3000 за ужин",
                    ),
                )
            ],
            cache_time=5,
            is_personal=True,
        )
        return

    amount, description = parsed

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
        await ExpenseRepo.set_inline_message_id(
            session, expense.id, chosen.inline_message_id
        )

    # Workaround: отправить фото в ЛС → получить file_id → удалить
    photo_msg = await bot.send_photo(
        chat_id=creator_id,
        photo=BufferedInputFile(result.card_image.read(), filename="card.png"),
    )
    file_id = photo_msg.photo[-1].file_id
    await bot.delete_message(chat_id=creator_id, message_id=photo_msg.message_id)

    # Сохранить file_id
    await ExpenseRepo.set_card_file_id(session, expense.id, file_id)

    # Обновить inline-сообщение: текст → фото + кнопки
    if chosen.inline_message_id:
        await bot.edit_message_media(
            inline_message_id=chosen.inline_message_id,
            media=InputMediaPhoto(media=file_id),
            reply_markup=expense_keyboard(expense.id),
        )
