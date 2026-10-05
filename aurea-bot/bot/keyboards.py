"""Inline- и reply-клавиатуры бота.

Callback-данные короткие (< 64 байт). Выбор пользователя хранится в FSM,
а не в callback_data.
"""
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

import config
from data import clinic, texts

# --- Константы callback_data ---
CB_CONSENT = "consent_agree"
CB_MENU = "menu"
CB_BOOK = "book"
CB_SERVICES = "services"
CB_DOCTOR = "doctor"
CB_CONTACTS = "contacts"
CB_MYBOOKINGS = "mybookings"
CB_CONFIRM = "confirm"
CB_CANCEL = "cancel"
PREFIX_SERVICE = "svc:"
PREFIX_DAY = "day:"
PREFIX_TIME = "tm:"
PREFIX_CANCEL_BOOKING = "cxl:"


def consent_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Соглашаюсь", callback_data=CB_CONSENT)
    b.button(text="📄 Политика конфиденциальности", url=config.POLICY_URL)
    b.button(text="📄 Согласие на обработку данных", url=config.CONSENT_URL)
    b.adjust(1)
    return b.as_markup()


def main_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📅 Записаться", callback_data=CB_BOOK)
    b.button(text="💉 Услуги и цены", callback_data=CB_SERVICES)
    b.button(text="👩‍⚕️ О враче", callback_data=CB_DOCTOR)
    b.button(text="📍 Контакты и адрес", callback_data=CB_CONTACTS)
    b.button(text="📋 Мои записи", callback_data=CB_MYBOOKINGS)
    b.adjust(1, 2, 2)
    return b.as_markup()


def back_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ В меню", callback_data=CB_MENU)
    b.adjust(1)
    return b.as_markup()


def contacts_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🗺 Открыть в Яндекс.Картах", url=clinic.YANDEX_MAPS_URL)
    b.button(text="⬅️ В меню", callback_data=CB_MENU)
    b.adjust(1)
    return b.as_markup()


def services_kb(services) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for service in services:
        b.button(
            text=f"{service['name']} — {service['price_label']}",
            callback_data=f"{PREFIX_SERVICE}{service['id']}",
        )
    b.button(text="⬅️ В меню", callback_data=CB_MENU)
    b.adjust(1)
    return b.as_markup()


def dates_kb(dates) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for d in dates:
        b.button(text=texts.fmt_date_btn(d), callback_data=f"{PREFIX_DAY}{d.isoformat()}")
    b.button(text="⬅️ В меню", callback_data=CB_MENU)
    # Даты по 2 в ряд, кнопка меню — отдельной строкой.
    rows = [2] * ((len(dates) + 1) // 2)
    b.adjust(*rows, 1) if rows else b.adjust(1)
    return b.as_markup()


def times_kb(times) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in times:
        b.button(text=t, callback_data=f"{PREFIX_TIME}{t}")
    b.button(text="⬅️ В меню", callback_data=CB_MENU)
    rows = [3] * ((len(times) + 2) // 3)
    b.adjust(*rows, 1) if rows else b.adjust(1)
    return b.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Подтвердить", callback_data=CB_CONFIRM)
    b.button(text="❌ Отменить", callback_data=CB_CANCEL)
    b.adjust(2)
    return b.as_markup()


def phone_kb() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.button(text="📱 Отправить номер", request_contact=True)
    return b.as_markup(resize_keyboard=True, one_time_keyboard=True)


def my_bookings_kb(bookings_list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for item in bookings_list:
        b.button(
            text=f"❌ {texts.fmt_date_btn(item['date'])} {item['time']}",
            callback_data=f"{PREFIX_CANCEL_BOOKING}{item['id']}",
        )
    b.button(text="⬅️ В меню", callback_data=CB_MENU)
    b.adjust(1)
    return b.as_markup()
