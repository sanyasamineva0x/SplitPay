from aiogram import Router

from bot.routers.inline import router as inline_router
from bot.routers.private import router as private_router

router = Router()
router.include_router(private_router)
router.include_router(inline_router)
