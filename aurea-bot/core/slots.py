"""Генерация доступных дат и свободных слотов.

Учитывает: рабочие часы по дню недели, сетку слотов, уже занятые записи,
прошедшее время и окно записи. Не зависит от aiogram.
"""
from datetime import date as _date, datetime, time as _time, timedelta

from config import TZ
from core import bookings
from data import schedule


def _now() -> datetime:
    return datetime.now(TZ)


def available_dates():
    """Список дат (date) в окне записи, у которых есть рабочие часы.

    Окно: со «завтра» (BOOKING_START_OFFSET_DAYS) до +BOOKING_WINDOW_DAYS.
    Сегодня не предлагается — чтобы не было записей задним числом.
    """
    today = _now().date()
    start = today + timedelta(days=schedule.BOOKING_START_OFFSET_DAYS)
    end = today + timedelta(days=schedule.BOOKING_WINDOW_DAYS)
    result = []
    current = start
    while current <= end:
        if schedule.working_hours_for(current.weekday()):
            result.append(current)
        current += timedelta(days=1)
    return result


async def free_slots(date_str: str, service_id: str | None = None):
    """Список свободных слотов 'HH:MM' на дату.

    service_id сейчас не влияет на длину (сетка округлена к 60 мин, любая
    услуга занимает один часовой слот), но параметр оставлен для будущего
    расширения (услуги длиннее 60 мин).
    """
    try:
        d = _date.fromisoformat(date_str)
    except ValueError:
        return []

    base = schedule.day_slots(d.weekday())
    if not base:
        return []

    occupied = await bookings.get_occupied_times(date_str)
    now = _now()

    free = []
    for slot in base:
        if slot in occupied:
            continue
        slot_dt = datetime.combine(d, _time.fromisoformat(slot), TZ)
        if slot_dt <= now:
            continue  # прошедшее время
        free.append(slot)
    return free
