from aiogram import Router

from bot.routers.callbacks import router as callbacks_router
from bot.routers.inline import router as inline_router
from bot.routers.private import router as private_router

router = Router()
router.include_router(private_router)
router.include_router(inline_router)
router.include_router(callbacks_router)
