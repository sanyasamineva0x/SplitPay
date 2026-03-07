import asyncio
import logging

from bot.app import create_bot, create_dispatcher
from bot.db.engine import create_tables


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    await create_tables()
    bot = create_bot()
    dp = create_dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
