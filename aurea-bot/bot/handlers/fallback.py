"""Фолбэк-хендлеры: устаревшие inline-кнопки и прочие сообщения.

Подключается ПОСЛЕДНИМ, чтобы ловить только то, что не обработали остальные
роутеры. Нажатие старых кнопок не должно ломать бота.
"""
import logging

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message

from data import texts

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query()
async def stale_callback(cb: CallbackQuery) -> None:
    """Любой необработанный callback — это устаревшая кнопка."""
    try:
        await cb.answer(texts.STALE, show_alert=True)
    except Exception:  # noqa: BLE001
        pass


@router.message(StateFilter(None))
async def fallback_message(message: Message) -> None:
    """Сообщение вне сценария — мягко направляем к /start.

    Меню не показываем намеренно: до согласия нельзя вести к сбору данных.
    """
    await message.answer(texts.FALLBACK)
