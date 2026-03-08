from aiogram.filters.callback_data import CallbackData


class ExpenseCallback(CallbackData, prefix="exp"):
    expense_id: int
    action: str  # "join" | "settle"
