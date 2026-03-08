import html
import re

from aiogram import Bot, F, Router
from aiogram.enums import ContentType
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories import UserRepo
from bot.keyboards import bank_selection_keyboard, phone_request_keyboard
from bot.states import OnboardingStates

router = Router()
PHONE_RE = re.compile(r"^\+7\d{10}$")
MAX_BANK_NAME_LEN = 50


@router.message(CommandStart())
async def cmd_start(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    await UserRepo.upsert(
        session,
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username,
    )

    user = await UserRepo.get_by_id(session, message.from_user.id)
    if user.is_onboarded:
        me = await bot.get_me()
        await message.answer(
            f"Ты уже настроен! Используй <b>@{me.username} сумма описание</b> в любом чате."
        )
        return

    name = html.escape(message.from_user.first_name)
    await state.set_state(OnboardingStates.waiting_phone)
    await message.answer(
        f"Привет, {name}! Я помогу разделить расходы между друзьями.\n\n"
        "Поделись номером телефона или введи вручную в формате <b>+7XXXXXXXXXX</b>, "
        "чтобы друзья знали куда переводить:",
        reply_markup=phone_request_keyboard(),
    )


async def _proceed_to_bank(message: Message, state: FSMContext, phone: str) -> None:
    """Общая логика после получения телефона: сохранить и показать банки."""
    await state.update_data(phone=phone)
    await state.set_state(OnboardingStates.waiting_bank)
    kb = bank_selection_keyboard()
    await message.answer("Номер сохранён!", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        "Выбери банк для приёма переводов:", reply_markup=kb.as_markup()
    )


@router.message(OnboardingStates.waiting_phone, F.content_type == ContentType.CONTACT)
async def process_phone_contact(message: Message, state: FSMContext) -> None:
    contact = message.contact
    if not contact or not contact.phone_number:
        await message.answer(
            "Не удалось получить номер. Введи вручную в формате <b>+7XXXXXXXXXX</b>:"
        )
        return

    phone = contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone

    await _proceed_to_bank(message, state, phone)


@router.message(OnboardingStates.waiting_phone)
async def process_phone_text(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer(
            "Введи номер в формате <b>+7XXXXXXXXXX</b> "
            "или нажми кнопку «📱 Поделиться номером»:"
        )
        return

    phone = message.text.strip()
    if not PHONE_RE.match(phone):
        await message.answer(
            "Неверный формат. Введи номер в формате <b>+7XXXXXXXXXX</b>:"
        )
        return

    await _proceed_to_bank(message, state, phone)


@router.callback_query(OnboardingStates.waiting_bank, F.data.startswith("bank:"))
async def process_bank(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    bank_value = callback.data.split(":")[1]

    if bank_value == "other":
        await state.set_state(OnboardingStates.waiting_custom_bank)
        await callback.message.edit_text("Введи название банка:")
        await callback.answer()
        return

    data = await state.get_data()
    phone = data["phone"]

    await UserRepo.set_onboarded(
        session,
        telegram_id=callback.from_user.id,
        phone=phone,
        bank_name=bank_value,
    )

    me = await bot.get_me()
    await state.clear()
    await callback.message.edit_text(
        "Готово! Теперь в любом чате набери:\n\n"
        f"<code>@{me.username} 500 за ужин</code>\n\n"
        "Бот создаст карточку — друзья смогут разделить счёт."
    )
    await callback.answer()


@router.message(OnboardingStates.waiting_custom_bank)
async def process_custom_bank(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    if not message.text or not message.text.strip():
        await message.answer("Название банка не может быть пустым. Введи название:")
        return

    bank_name = message.text.strip()
    if len(bank_name) > MAX_BANK_NAME_LEN:
        await message.answer(
            f"Слишком длинное название (макс. {MAX_BANK_NAME_LEN} символов). Попробуй ещё:"
        )
        return

    data = await state.get_data()
    phone = data["phone"]

    await UserRepo.set_onboarded(
        session,
        telegram_id=message.from_user.id,
        phone=phone,
        bank_name=bank_name,
    )

    me = await bot.get_me()
    await state.clear()
    await message.answer(
        "Готово! Теперь в любом чате набери:\n\n"
        f"<code>@{me.username} 500 за ужин</code>\n\n"
        "Бот создаст карточку — друзья смогут разделить счёт."
    )
