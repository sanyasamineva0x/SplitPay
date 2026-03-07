from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    waiting_phone = State()
    waiting_bank = State()
