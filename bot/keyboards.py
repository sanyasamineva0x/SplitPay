from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.callback_data import ExpenseCallback
from bot.enums import BankName

BANK_LABELS: dict[str, str] = {
    BankName.SBER: "Сбер",
    BankName.TINKOFF: "Т-Банк",
    BankName.ALFA: "Альфа",
    BankName.VTB: "ВТБ",
    BankName.RAIFFEISEN: "Райффайзен",
}


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


def bank_selection_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for bank_id, label in BANK_LABELS.items():
        builder.add(InlineKeyboardButton(text=label, callback_data=f"bank:{bank_id}"))
    builder.adjust(2)
    return builder
