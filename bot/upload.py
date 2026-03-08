"""Утилита для загрузки фото в Telegram и получения file_id."""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import BufferedInputFile

from bot.config import get_settings

logger = logging.getLogger(__name__)


async def upload_photo(bot: Bot, image_bytes: bytes, fallback_chat_id: int) -> str:
    """Загрузить фото → получить file_id.

    Использует служебный канал (UPLOAD_CHAT_ID) если задан,
    иначе — ЛС fallback_chat_id (с удалением сообщения).
    """
    settings = get_settings()
    upload_target = settings.upload_chat_id or fallback_chat_id
    photo_msg = await bot.send_photo(
        chat_id=upload_target,
        photo=BufferedInputFile(image_bytes, filename="card.png"),
    )
    file_id = photo_msg.photo[-1].file_id
    # В канале оставляем (хранилище), в ЛС — удаляем (не спамим)
    if not settings.upload_chat_id:
        await bot.delete_message(chat_id=upload_target, message_id=photo_msg.message_id)
    return file_id
