"""Все тексты бота на русском языке. Единый источник правды по контенту.

Правка формулировок происходит здесь и не требует изменений в хендлерах.
Динамические тексты (списки услуг, даты, сводка записи) собираются функциями,
но шаблоны и слова — тоже здесь.
"""
from datetime import date as _date
from html import escape

from data import clinic, load_services

# --- Служебные справочники для форматирования дат ---
WEEKDAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_GEN = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]
MONTHS_SHORT = [
    "янв", "фев", "мар", "апр", "мая", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
]


def _as_date(value):
    if isinstance(value, str):
        return _date.fromisoformat(value)
    return value


def fmt_date_long(value) -> str:
    """'Пн, 6 октября' — для сообщений."""
    d = _as_date(value)
    return f"{WEEKDAYS_SHORT[d.weekday()]}, {d.day} {MONTHS_GEN[d.month - 1]}"


def fmt_date_btn(value) -> str:
    """'Пн 6 окт' — для кнопок (короче)."""
    d = _as_date(value)
    return f"{WEEKDAYS_SHORT[d.weekday()]} {d.day} {MONTHS_SHORT[d.month - 1]}"


# ======================= Статические тексты =======================

GREETING = (
    "<b>Aurea</b> — студия эстетической косметологии в центре Москвы.\n\n"
    "Онлайн-запись к врачу-косметологу за пару шагов."
)

CONSENT_TEXT = (
    "Прежде чем продолжить, нужно ваше согласие на обработку персональных данных.\n\n"
    "Для записи мы обрабатываем только <b>имя</b> и <b>номер телефона</b> — чтобы "
    "подтвердить визит и напомнить о нём. Данные хранятся локально и не передаются "
    "третьим лицам (152-ФЗ).\n\n"
    "В чате мы <b>не спрашиваем</b> о жалобах, диагнозах и состоянии здоровья — "
    "это вы обсудите с врачом на приёме.\n\n"
    "Нажимая «Соглашаюсь», вы подтверждаете согласие на обработку персональных "
    "данных и принятие политики конфиденциальности."
)

CONSENT_DONE = "Спасибо! Согласие сохранено. 🤍"

NEED_CONSENT = (
    "Чтобы записаться, нужно согласие на обработку данных. "
    "Нажмите /start и подтвердите согласие."
)

MENU_TITLE = "Выберите раздел:"

FALLBACK = "Чтобы начать, нажмите /start 🙂"

ERROR_GENERIC = (
    "Что-то пошло не так. Попробуйте ещё раз или начните заново: /start"
)

# --- Услуги ---
SERVICES_HEADER = "💉 <b>Услуги и цены</b>"
PRICES_NOTE = (
    "Цены указаны ориентировочно. Точную стоимость врач озвучит после консультации."
)
FIRST_VISIT_NOTE = (
    "Первый визит по любой услуге включает бесплатную консультацию врача."
)

# --- Запись ---
CHOOSE_SERVICE = "Выберите услугу:"
CHOOSE_DATE = "Выберите дату визита:"
ENTER_NAME = (
    "Как к вам обращаться? Напишите имя (от 2 до 50 символов, без ссылок)."
)
ENTER_PHONE = (
    "Оставьте номер телефона для подтверждения записи.\n"
    "Нажмите кнопку ниже или введите вручную в формате <b>+7XXXXXXXXXX</b>."
)
PHONE_SAVED = "Номер сохранён."
BAD_NAME = (
    "Имя должно быть от 2 до 50 символов, без ссылок и упоминаний (@). "
    "Попробуйте ещё раз."
)
BAD_PHONE = (
    "Не удалось распознать номер. Введите российский номер в формате "
    "+7XXXXXXXXXX или 8XXXXXXXXXX."
)
NO_SLOTS = (
    "На эту дату свободного времени нет. Пожалуйста, выберите другую дату:"
)
SLOT_TAKEN = (
    "К сожалению, это время только что заняли. Выберите, пожалуйста, другую дату или время:"
)
LIMIT_REACHED = (
    "У вас уже 3 активные записи — это максимум. Чтобы записаться снова, "
    "отмените одну из записей в разделе «Мои записи»."
)
BOOKING_INVALID = (
    "Выбранные дата или время недоступны. Начните запись заново: /start"
)
BOOKING_CANCELLED_FLOW = "Запись отменена. Вы можете начать заново в любой момент."
NO_BOOKINGS = "У вас пока нет активных записей."
STALE = "Начните заново: /start"


def choose_time(date_value) -> str:
    return f"Свободное время на <b>{fmt_date_long(date_value)}</b>:"


# ======================= Динамические тексты =======================

def services_list() -> str:
    lines = [SERVICES_HEADER, ""]
    for service in load_services():
        lines.append(f"• <b>{service['name']}</b> — {service['price_label']}")
        note = service.get("note")
        if note:
            lines.append(f"  <i>{note}</i>")
    lines += [
        "",
        FIRST_VISIT_NOTE,
        PRICES_NOTE,
        "",
        "Нажмите на услугу, чтобы записаться 👇",
    ]
    return "\n".join(lines)


DOCTOR = (
    "👩‍⚕️ <b>О враче</b>\n\n"
    f"<b>{clinic.DOCTOR_NAME}</b> — {clinic.DOCTOR_INFO}.\n\n"
    f"Лицензия: {clinic.LICENSE}."
)

CONTACTS = (
    f"📍 <b>{clinic.BRAND}</b>\n\n"
    f"Адрес: {clinic.ADDRESS}\n"
    f"Метро: {clinic.METRO}\n"
    f"Часы работы: {clinic.HOURS}\n"
    f"Телефон: {clinic.PHONE}\n"
    f"Email: {clinic.EMAIL}\n\n"
    f"⚠️ {clinic.DISCLAIMER}"
)


def booking_summary(service_name, date_value, time_str, name, phone) -> str:
    return (
        "Проверьте запись:\n\n"
        f"💉 Услуга: <b>{escape(service_name)}</b>\n"
        f"📅 Дата: <b>{fmt_date_long(date_value)}</b>\n"
        f"🕐 Время: <b>{time_str}</b>\n"
        f"👤 Имя: <b>{escape(name)}</b>\n"
        f"📱 Телефон: <b>{escape(phone)}</b>"
    )


def booking_success(service_name, date_value, time_str) -> str:
    return (
        "✅ <b>Вы записаны!</b>\n\n"
        f"💉 {escape(service_name)}\n"
        f"📅 {fmt_date_long(date_value)} в {time_str}\n"
        f"📍 {clinic.ADDRESS}\n\n"
        f"{FIRST_VISIT_NOTE}\n\n"
        "Если планы изменятся — отмените запись в разделе «Мои записи»."
    )


def my_bookings_header(bookings_list) -> str:
    if not bookings_list:
        return NO_BOOKINGS
    lines = ["📋 <b>Ваши записи</b>\n"]
    for b in bookings_list:
        lines.append(
            f"• {fmt_date_long(b['date'])} в {b['time']} — {escape(b['service_name'])}"
        )
    lines.append("\nЧтобы отменить запись — нажмите кнопку ниже.")
    return "\n".join(lines)


def reminder(service_name, date_value, time_str, kind: str) -> str:
    when = "за 24 часа" if kind == "24h" else "за 2 часа"
    return (
        f"⏰ <b>Напоминание о визите</b> ({when})\n\n"
        "Ждём вас в Aurea:\n"
        f"💉 {escape(service_name)}\n"
        f"📅 {fmt_date_long(date_value)} в {time_str}\n"
        f"📍 {clinic.ADDRESS}"
    )


# ======================= Тексты для администратора =======================

def admin_new_booking(b) -> str:
    return (
        "🆕 <b>Новая запись</b>\n\n"
        f"💉 {escape(b['service_name'])}\n"
        f"📅 {fmt_date_long(b['date'])} в {b['time']}\n"
        f"👤 {escape(b['name'])}\n"
        f"📱 {escape(b['phone'])}\n"
        f"🆔 user_id: {b['user_id']}"
    )


def admin_bookings_list(bookings_list) -> str:
    if not bookings_list:
        return "Предстоящих записей нет."
    lines = ["📋 <b>Предстоящие записи</b>\n"]
    for b in bookings_list:
        lines.append(
            f"• {fmt_date_long(b['date'])} {b['time']} — {escape(b['service_name'])} — "
            f"{escape(b['name'])} — {escape(b['phone'])}"
        )
    return "\n".join(lines)
