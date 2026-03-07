from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import get_settings
from bot.routers import router


def create_bot() -> Bot:
    return Bot(
        token=get_settings().bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(router)
    return dp
