"""Раздел «Мои записи»: список будущих записей и отмена."""
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot import keyboards as kb
from core import bookings
from data import texts

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == kb.CB_MYBOOKINGS)
async def show_my_bookings(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        items = await bookings.get_user_bookings(cb.from_user.id)
    except Exception:  # noqa: BLE001
        logger.exception("Ошибка получения записей пользователя")
        await cb.answer(texts.ERROR_GENERIC, show_alert=True)
        return
    await cb.message.answer(texts.my_bookings_header(items), reply_markup=kb.my_bookings_kb(items))
    await cb.answer()


@router.callback_query(F.data.startswith(kb.PREFIX_CANCEL_BOOKING))
async def cancel_booking(cb: CallbackQuery) -> None:
    raw = cb.data[len(kb.PREFIX_CANCEL_BOOKING):]
    try:
        booking_id = int(raw)
    except ValueError:
        await cb.answer(texts.STALE, show_alert=True)
        return

    try:
        ok = await bookings.cancel_booking(booking_id, cb.from_user.id)
    except Exception:  # noqa: BLE001
        logger.exception("Ошибка отмены записи")
        await cb.answer(texts.ERROR_GENERIC, show_alert=True)
        return

    await cb.answer("Запись отменена." if ok else "Эта запись уже отменена.",
                    show_alert=not ok)

    # Перерисовываем список.
    try:
        items = await bookings.get_user_bookings(cb.from_user.id)
        await cb.message.edit_text(
            texts.my_bookings_header(items), reply_markup=kb.my_bookings_kb(items)
        )
    except Exception:  # noqa: BLE001 — сообщение могло не измениться/устареть
        try:
            items = await bookings.get_user_bookings(cb.from_user.id)
            await cb.message.answer(
                texts.my_bookings_header(items), reply_markup=kb.my_bookings_kb(items)
            )
        except Exception:  # noqa: BLE001
            logger.exception("Не удалось обновить список записей")
