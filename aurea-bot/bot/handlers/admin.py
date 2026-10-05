"""Администратор: уведомление о новой записи, /bookings, /test_reminder."""
import logging
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import config
from core import bookings
from data import texts

logger = logging.getLogger(__name__)
router = Router()


def _is_admin(user_id: int) -> bool:
    return config.ADMIN_CHAT_ID is not None and user_id == config.ADMIN_CHAT_ID


async def notify_new_booking(bot, booking: dict) -> None:
    """Отправляет администратору уведомление о новой записи.

    Вызывается из сценария записи. Ошибка отправки не ломает запись клиента.
    """
    if config.ADMIN_CHAT_ID is None:
        logger.warning("ADMIN_CHAT_ID не задан — уведомление администратору не отправлено")
        return
    try:
        await bot.send_message(config.ADMIN_CHAT_ID, texts.admin_new_booking(booking))
    except Exception:  # noqa: BLE001
        logger.exception("Не удалось отправить уведомление администратору")


@router.message(Command("bookings"))
async def cmd_bookings(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return  # команда только для администратора
    try:
        items = await bookings.get_all_upcoming()
    except Exception:  # noqa: BLE001
        logger.exception("Ошибка получения списка записей")
        await message.answer(texts.ERROR_GENERIC)
        return
    await message.answer(texts.admin_bookings_list(items))


@router.message(Command("test_reminder"))
async def cmd_test_reminder(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return
    tomorrow = (datetime.now(config.TZ) + timedelta(days=1)).date().isoformat()
    await message.answer(
        texts.reminder("Консультация косметолога", tomorrow, "12:00", "24h")
    )
