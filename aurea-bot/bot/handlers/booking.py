"""Сценарий записи (FSM): услуга → дата → время → имя → телефон → подтверждение."""
import logging
from datetime import date as _date

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from bot import keyboards as kb
from bot.handlers.admin import notify_new_booking
from bot.states import Booking
from core import bookings, consent, slots, validation
from core.bookings import (
    BookingLimitError,
    InvalidSlotError,
    PastSlotError,
    SlotTakenError,
    UnknownServiceError,
)
from data import get_service, load_services, schedule, texts

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == kb.CB_BOOK)
async def start_booking(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()

    # Согласие обязательно до сбора ПДн.
    try:
        agreed = await consent.has_consent(cb.from_user.id)
    except Exception:  # noqa: BLE001
        logger.exception("Ошибка проверки согласия")
        agreed = False
    if not agreed:
        await cb.message.answer(texts.NEED_CONSENT)
        await cb.answer()
        return

    # Лимит активных записей.
    try:
        active = await bookings.count_active(cb.from_user.id)
    except Exception:  # noqa: BLE001
        logger.exception("Ошибка подсчёта активных записей")
        active = 0
    if active >= schedule.MAX_ACTIVE_BOOKINGS:
        await cb.message.answer(texts.LIMIT_REACHED, reply_markup=kb.back_menu_kb())
        await cb.answer()
        return

    await state.set_state(Booking.service)
    await cb.message.answer(texts.CHOOSE_SERVICE, reply_markup=kb.services_kb(load_services()))
    await cb.answer()


@router.callback_query(F.data.startswith(kb.PREFIX_SERVICE))
async def choose_service(cb: CallbackQuery, state: FSMContext) -> None:
    """Выбор услуги. Работает в двух сценариях:

    1) Внутри сценария записи (пользователь нажал «Записаться», выбирает услугу).
    2) Напрямую из раздела «Услуги и цены» — тогда ещё нужно проверить
       согласие и лимит активных записей, прежде чем вести к выбору даты.
    """
    service_id = cb.data[len(kb.PREFIX_SERVICE):]
    service = get_service(service_id)
    if not service:
        await state.clear()
        await cb.answer(texts.STALE, show_alert=True)
        return

    # Прямой заход из раздела услуг — не в состоянии Booking.service.
    current_state = await state.get_state()
    if current_state != Booking.service.state:
        try:
            agreed = await consent.has_consent(cb.from_user.id)
        except Exception:  # noqa: BLE001
            logger.exception("Ошибка проверки согласия")
            agreed = False
        if not agreed:
            await cb.message.answer(texts.NEED_CONSENT)
            await cb.answer()
            return

        try:
            active = await bookings.count_active(cb.from_user.id)
        except Exception:  # noqa: BLE001
            logger.exception("Ошибка подсчёта активных записей")
            active = 0
        if active >= schedule.MAX_ACTIVE_BOOKINGS:
            await cb.message.answer(texts.LIMIT_REACHED, reply_markup=kb.back_menu_kb())
            await cb.answer()
            return

    await state.update_data(service_id=service_id, service_name=service["name"])
    await state.set_state(Booking.date)
    await cb.message.answer(texts.CHOOSE_DATE, reply_markup=kb.dates_kb(slots.available_dates()))
    await cb.answer()


@router.callback_query(StateFilter(Booking.date), F.data.startswith(kb.PREFIX_DAY))
async def choose_date(cb: CallbackQuery, state: FSMContext) -> None:
    date_str = cb.data[len(kb.PREFIX_DAY):]
    try:
        chosen = _date.fromisoformat(date_str)
    except ValueError:
        await cb.answer(texts.STALE, show_alert=True)
        return

    if chosen not in slots.available_dates():
        await cb.answer("Эта дата больше недоступна. Выберите другую.", show_alert=True)
        await cb.message.answer(texts.CHOOSE_DATE, reply_markup=kb.dates_kb(slots.available_dates()))
        return

    data = await state.get_data()
    free = await slots.free_slots(date_str, data.get("service_id"))
    if not free:
        await cb.answer()
        await cb.message.answer(texts.NO_SLOTS, reply_markup=kb.dates_kb(slots.available_dates()))
        return

    await state.update_data(date=date_str)
    await state.set_state(Booking.time)
    await cb.message.answer(texts.choose_time(date_str), reply_markup=kb.times_kb(free))
    await cb.answer()


@router.callback_query(StateFilter(Booking.time), F.data.startswith(kb.PREFIX_TIME))
async def choose_time(cb: CallbackQuery, state: FSMContext) -> None:
    time_str = cb.data[len(kb.PREFIX_TIME):]
    data = await state.get_data()
    date_str = data.get("date")
    if not date_str:
        await state.clear()
        await cb.answer(texts.STALE, show_alert=True)
        return

    free = await slots.free_slots(date_str, data.get("service_id"))
    if time_str not in free:
        await cb.answer("Это время только что заняли. Выберите другое.", show_alert=True)
        if free:
            await cb.message.answer(texts.choose_time(date_str), reply_markup=kb.times_kb(free))
        else:
            await cb.message.answer(texts.NO_SLOTS, reply_markup=kb.dates_kb(slots.available_dates()))
        return

    await state.update_data(time=time_str)
    await state.set_state(Booking.name)
    await cb.message.answer(texts.ENTER_NAME)
    await cb.answer()


@router.message(StateFilter(Booking.name))
async def enter_name(message: Message, state: FSMContext) -> None:
    name = validation.validate_name(message.text)
    if not name:
        await message.answer(texts.BAD_NAME)
        return
    await state.update_data(name=name)
    await state.set_state(Booking.phone)
    await message.answer(texts.ENTER_PHONE, reply_markup=kb.phone_kb())


@router.message(StateFilter(Booking.phone))
async def enter_phone(message: Message, state: FSMContext) -> None:
    if message.contact is not None:
        raw = message.contact.phone_number
    elif message.text:
        raw = message.text
    else:
        await message.answer(texts.BAD_PHONE)
        return

    phone = validation.normalize_phone(raw)
    if not phone:
        await message.answer(texts.BAD_PHONE)
        return

    await state.update_data(phone=phone)
    data = await state.get_data()
    await state.set_state(Booking.confirm)
    await message.answer(texts.PHONE_SAVED, reply_markup=ReplyKeyboardRemove())
    await message.answer(
        texts.booking_summary(
            data["service_name"], data["date"], data["time"], data["name"], phone
        ),
        reply_markup=kb.confirm_kb(),
    )


@router.callback_query(StateFilter(Booking.confirm), F.data == kb.CB_CONFIRM)
async def confirm_booking(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    required = ("service_id", "service_name", "date", "time", "name", "phone")
    if not all(key in data for key in required):
        await state.clear()
        await cb.answer(texts.STALE, show_alert=True)
        return

    try:
        await bookings.create_booking(
            cb.from_user.id,
            data["service_id"],
            data["date"],
            data["time"],
            data["name"],
            data["phone"],
        )
    except SlotTakenError:
        await state.set_state(Booking.date)
        await cb.message.answer(texts.SLOT_TAKEN, reply_markup=kb.dates_kb(slots.available_dates()))
        await cb.answer()
        return
    except BookingLimitError:
        await state.clear()
        await cb.message.answer(texts.LIMIT_REACHED, reply_markup=kb.back_menu_kb())
        await cb.answer()
        return
    except (PastSlotError, InvalidSlotError, UnknownServiceError):
        await state.clear()
        await cb.message.answer(texts.BOOKING_INVALID, reply_markup=kb.back_menu_kb())
        await cb.answer()
        return
    except Exception:  # noqa: BLE001
        logger.exception("Ошибка создания записи")
        await state.clear()
        await cb.message.answer(texts.ERROR_GENERIC, reply_markup=kb.back_menu_kb())
        await cb.answer()
        return

    # Готовим данные для успеха/админа до очистки стейта.
    booking_info = {
        "user_id": cb.from_user.id,
        "service_name": data["service_name"],
        "date": data["date"],
        "time": data["time"],
        "name": data["name"],
        "phone": data["phone"],
    }
    await state.clear()

    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001
        pass

    await cb.message.answer(
        texts.booking_success(booking_info["service_name"], booking_info["date"],
                              booking_info["time"]),
        reply_markup=kb.back_menu_kb(),
    )
    await notify_new_booking(cb.bot, booking_info)
    await cb.answer("Готово!")


@router.callback_query(StateFilter(Booking.confirm), F.data == kb.CB_CANCEL)
async def cancel_flow(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001
        pass
    await cb.message.answer(texts.BOOKING_CANCELLED_FLOW, reply_markup=kb.main_menu())
    await cb.answer()
