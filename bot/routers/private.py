import re

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories import UserRepo
from bot.keyboards import bank_selection_keyboard
from bot.states import OnboardingStates

router = Router()
PHONE_RE = re.compile(r"^\+7\d{10}$")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await UserRepo.upsert(
        session,
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username,
    )

    user = await UserRepo.get_by_id(session, message.from_user.id)
    if user.is_onboarded:
        await message.answer(
            "Ты уже настроен! Используй <b>@TGpayBot сумма описание</b> в любом чате."
        )
        return

    await state.set_state(OnboardingStates.waiting_phone)
    await message.answer(
        "Привет! Я помогу создавать запросы на оплату через СБП.\n\n"
        "Введи номер телефона в формате <b>+7XXXXXXXXXX</b>:"
    )


@router.message(OnboardingStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip()
    if not PHONE_RE.match(phone):
        await message.answer(
            "Неверный формат. Введи номер в формате <b>+7XXXXXXXXXX</b>:"
        )
        return

    await state.update_data(phone=phone)
    await state.set_state(OnboardingStates.waiting_bank)

    kb = bank_selection_keyboard()
    await message.answer("Выбери банк для приёма СБП:", reply_markup=kb.as_markup())


@router.callback_query(OnboardingStates.waiting_bank, F.data.startswith("bank:"))
async def process_bank(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    bank_name = callback.data.split(":")[1]
    data = await state.get_data()
    phone = data["phone"]

    await UserRepo.set_onboarded(
        session,
        telegram_id=callback.from_user.id,
        phone=phone,
        bank_name=bank_name,
    )

    await state.clear()
    await callback.message.edit_text(
        "Готово! Теперь используй <b>@TGpayBot сумма описание</b> в любом чате.\n\n"
        "Пример: <code>@TGpayBot 500 за ужин</code>"
    )
    await callback.answer()
