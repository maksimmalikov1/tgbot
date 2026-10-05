"""/start и экран согласия (152-ФЗ) до любого сбора данных."""
import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import keyboards as kb
from core import consent
from data import texts

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    try:
        agreed = await consent.has_consent(message.from_user.id)
    except Exception:  # noqa: BLE001
        logger.exception("Ошибка проверки согласия")
        agreed = False

    if agreed:
        await message.answer(texts.MENU_TITLE, reply_markup=kb.main_menu())
    else:
        await message.answer(texts.GREETING)
        await message.answer(texts.CONSENT_TEXT, reply_markup=kb.consent_kb())


@router.callback_query(F.data == kb.CB_CONSENT)
async def on_consent(cb: CallbackQuery, state: FSMContext) -> None:
    try:
        await consent.save_consent(cb.from_user.id, cb.from_user.full_name)
    except Exception:  # noqa: BLE001
        logger.exception("Не удалось сохранить согласие")
        await cb.answer("Не удалось сохранить согласие. Попробуйте ещё раз.",
                        show_alert=True)
        return

    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001 — сообщение могло устареть
        pass

    await cb.message.answer(texts.CONSENT_DONE)
    await cb.message.answer(texts.MENU_TITLE, reply_markup=kb.main_menu())
    await cb.answer()
