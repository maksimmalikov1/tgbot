"""Бизнес-логика записей: создание, отмена, список, проверка слотов.

Не зависит от aiogram — функции принимают примитивы и возвращают
примитивы/исключения. Это транспортно-независимый слой.

TODO (HTTP API для сайта): эти же функции (create_booking, cancel_booking,
get_user_bookings, is_slot_free, get_occupied_times, count_active) пригодны
как основа REST-эндпоинтов — достаточно обернуть их в HTTP-обработчики
(например, на aiohttp/FastAPI), не меняя саму логику. Сам эндпоинт здесь
НЕ реализуется намеренно.
"""
import sqlite3
from datetime import date as _date, datetime, time as _time, timedelta

import aiosqlite

from config import TZ
from core import db
from data import get_service, schedule


class BookingError(Exception):
    """Базовая ошибка бизнес-логики записи."""


class SlotTakenError(BookingError):
    """Слот уже занят (в т.ч. гонка на шаге подтверждения)."""


class BookingLimitError(BookingError):
    """Превышен лимит активных записей пользователя."""


class PastSlotError(BookingError):
    """Выбранные дата/время уже в прошлом."""


class InvalidSlotError(BookingError):
    """Время не попадает в рабочую сетку слотов для этого дня."""


class UnknownServiceError(BookingError):
    """Неизвестная услуга."""


def _now() -> datetime:
    return datetime.now(TZ)


def _now_key() -> str:
    """Строковый ключ 'YYYY-MM-DD HH:MM' для сравнения со слотами в SQL."""
    return _now().strftime("%Y-%m-%d %H:%M")


def visit_datetime(date_str: str, time_str: str) -> datetime:
    """Собирает aware-datetime визита в таймзоне клиники."""
    d = _date.fromisoformat(date_str)
    t = _time.fromisoformat(time_str)
    return datetime.combine(d, t, TZ)


async def count_active(user_id: int) -> int:
    """Количество активных будущих записей пользователя."""
    async with db.connect() as conn:
        cur = await conn.execute(
            "SELECT COUNT(*) FROM bookings "
            "WHERE user_id = ? AND status = 'active' "
            "AND (date || ' ' || time) > ?",
            (user_id, _now_key()),
        )
        (count,) = await cur.fetchone()
    return count


async def is_slot_free(date_str: str, time_str: str) -> bool:
    """True, если на (date, time) нет активной записи."""
    async with db.connect() as conn:
        cur = await conn.execute(
            "SELECT 1 FROM bookings "
            "WHERE date = ? AND time = ? AND status = 'active' LIMIT 1",
            (date_str, time_str),
        )
        row = await cur.fetchone()
    return row is None


async def get_occupied_times(date_str: str) -> set:
    """Множество занятых времён 'HH:MM' на дату (активные записи)."""
    async with db.connect() as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT time FROM bookings WHERE date = ? AND status = 'active'",
            (date_str,),
        )
        rows = await cur.fetchall()
    return {row["time"] for row in rows}


async def create_booking(
    user_id: int,
    service_id: str,
    date_str: str,
    time_str: str,
    name: str,
    phone: str,
) -> int:
    """Создаёт запись. Возвращает id. Бросает BookingError при проблемах.

    Проверки: существование услуги, корректность слота по сетке дня,
    визит не в прошлом, лимит активных записей, занятость слота
    (последнее — на уровне БД через уникальный индекс, защита от гонки).
    """
    service = get_service(service_id)
    if not service:
        raise UnknownServiceError(service_id)

    # Дата должна парситься и попадать в рабочую сетку этого дня недели.
    try:
        d = _date.fromisoformat(date_str)
    except ValueError as exc:
        raise InvalidSlotError(date_str) from exc
    if time_str not in schedule.day_slots(d.weekday()):
        raise InvalidSlotError(f"{date_str} {time_str}")

    # Визит не в прошлом.
    if visit_datetime(date_str, time_str) <= _now():
        raise PastSlotError(f"{date_str} {time_str}")

    # Лимит активных записей.
    if await count_active(user_id) >= schedule.MAX_ACTIVE_BOOKINGS:
        raise BookingLimitError()

    created_at = _now().isoformat()
    async with db.connect() as conn:
        try:
            cur = await conn.execute(
                "INSERT INTO bookings "
                "(user_id, service_id, service_name, date, time, name, phone, "
                " status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)",
                (user_id, service_id, service["name"], date_str, time_str,
                 name, phone, created_at),
            )
            await conn.commit()
            return cur.lastrowid
        except (sqlite3.IntegrityError, aiosqlite.IntegrityError):
            # Сработал уникальный индекс uniq_active_slot — слот заняли.
            raise SlotTakenError(f"{date_str} {time_str}")


async def cancel_booking(booking_id: int, user_id: int) -> bool:
    """Отменяет активную запись пользователя. True, если что-то отменили.

    Статус меняется на 'cancelled' — слот автоматически освобождается
    (уникальный индекс считает только активные записи).
    """
    async with db.connect() as conn:
        cur = await conn.execute(
            "UPDATE bookings SET status = 'cancelled' "
            "WHERE id = ? AND user_id = ? AND status = 'active'",
            (booking_id, user_id),
        )
        await conn.commit()
        return cur.rowcount > 0


async def get_user_bookings(user_id: int):
    """Список активных будущих записей пользователя (по возрастанию даты/времени)."""
    async with db.connect() as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT id, service_id, service_name, date, time, name, phone "
            "FROM bookings "
            "WHERE user_id = ? AND status = 'active' "
            "AND (date || ' ' || time) > ? "
            "ORDER BY date, time",
            (user_id, _now_key()),
        )
        rows = await cur.fetchall()
    return [dict(row) for row in rows]


async def get_all_upcoming():
    """Все активные будущие записи (для администратора)."""
    async with db.connect() as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT id, user_id, service_id, service_name, date, time, name, phone "
            "FROM bookings "
            "WHERE status = 'active' AND (date || ' ' || time) > ? "
            "ORDER BY date, time",
            (_now_key(),),
        )
        rows = await cur.fetchall()
    return [dict(row) for row in rows]


async def get_due_reminders(now: datetime):
    """Список напоминаний, которые пора обработать на момент `now`.

    Возвращает список словарей с ключами: id, user_id, service_name, date,
    time, kind ('24h'|'2h'), send (bool — отправлять ли сейчас или только
    пометить как обработанное, если момент пропущен).
    """
    out = []
    async with db.connect() as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT * FROM bookings WHERE status = 'active'"
        )
        rows = await cur.fetchall()

    grace = timedelta(hours=1)  # допускаем до часа простоя планировщика
    for row in rows:
        try:
            vdt = visit_datetime(row["date"], row["time"])
        except ValueError:
            continue
        if vdt <= now:
            continue  # визит уже прошёл — напоминать не нужно
        for hours, flag, kind in (
            (24, "reminded_24h", "24h"),
            (2, "reminded_2h", "2h"),
        ):
            if row[flag]:
                continue
            target = vdt - timedelta(hours=hours)
            if now >= target:
                out.append({
                    "id": row["id"],
                    "user_id": row["user_id"],
                    "service_name": row["service_name"],
                    "date": row["date"],
                    "time": row["time"],
                    "kind": kind,
                    "send": now <= target + grace,
                })
    return out


async def mark_reminded(booking_id: int, kind: str) -> None:
    """Помечает напоминание ('24h'|'2h') как обработанное."""
    column = "reminded_24h" if kind == "24h" else "reminded_2h"
    async with db.connect() as conn:
        await conn.execute(
            f"UPDATE bookings SET {column} = 1 WHERE id = ?",  # column из белого списка
            (booking_id,),
        )
        await conn.commit()
