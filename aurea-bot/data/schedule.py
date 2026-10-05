"""Расписание клиники: рабочие часы, сетка слотов, окно записи, напоминания.

Чистые данные + простые функции над ними. Не зависит от aiogram и БД.
Правка расписания происходит здесь и нигде больше.
"""
from config import TZ, TIMEZONE  # re-export, чтобы расписание было единой точкой

__all__ = [
    "TZ",
    "TIMEZONE",
    "WORKING_HOURS",
    "SLOT_MINUTES",
    "BOOKING_START_OFFSET_DAYS",
    "BOOKING_WINDOW_DAYS",
    "REMINDER_HOURS",
    "MAX_ACTIVE_BOOKINGS",
    "working_hours_for",
    "day_slots",
]

# Рабочие часы по дню недели.
# Ключ — weekday() из datetime: 0=Пн, 1=Вт, ... 5=Сб, 6=Вс.
# Значение — (час_открытия, час_закрытия) в 24-часовом формате.
WORKING_HOURS = {
    0: (9, 21),   # Пн
    1: (9, 21),   # Вт
    2: (9, 21),   # Ср
    3: (9, 21),   # Чт
    4: (9, 21),   # Пт
    5: (9, 21),   # Сб
    6: (10, 19),  # Вс
}

# Длина слота в минутах. Сетка округляется к этому значению.
SLOT_MINUTES = 60

# Окно записи: со «завтра» (offset=1) и на сколько дней вперёд.
BOOKING_START_OFFSET_DAYS = 1
BOOKING_WINDOW_DAYS = 14

# За сколько часов до визита напоминать клиенту.
REMINDER_HOURS = (24, 2)

# Лимит активных (будущих) записей на одного пользователя.
MAX_ACTIVE_BOOKINGS = 3


def working_hours_for(weekday: int):
    """Возвращает (open_hour, close_hour) или None, если день нерабочий."""
    return WORKING_HOURS.get(weekday)


def day_slots(weekday: int):
    """Все слоты (строки 'HH:MM') для дня недели по сетке SLOT_MINUTES.

    Слот считается допустимым, если целиком помещается в рабочие часы.
    Не учитывает занятость и прошедшее время — это делает core/slots.py.
    """
    hours = working_hours_for(weekday)
    if not hours:
        return []
    open_h, close_h = hours
    step_h = max(1, SLOT_MINUTES // 60)
    # Последний старт такой, что слот заканчивается не позже закрытия.
    return [f"{h:02d}:00" for h in range(open_h, close_h - step_h + 1, step_h)]
