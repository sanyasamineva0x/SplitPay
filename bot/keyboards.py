from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.enums import BankName

BANK_LABELS: dict[str, str] = {
    BankName.SBER: "Сбер",
    BankName.TINKOFF: "Т-Банк",
    BankName.ALFA: "Альфа",
    BankName.VTB: "ВТБ",
    BankName.RAIFFEISEN: "Райффайзен",
}


def bank_selection_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for bank_id, label in BANK_LABELS.items():
        builder.add(InlineKeyboardButton(text=label, callback_data=f"bank:{bank_id}"))
    builder.adjust(2)
    return builder
