from aiogram import Router

from bot.routers.private import router as private_router

router = Router()
router.include_router(private_router)
