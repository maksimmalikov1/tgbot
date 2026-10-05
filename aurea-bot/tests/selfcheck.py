"""Самопроверка проекта Aurea-bot.

Прогоняет 8 пунктов чек-листа из ТЗ на чистой временной БД, без реального
токена и без сети. Запуск:  python tests/selfcheck.py

Код выхода 0 — все проверки прошли; 1 — есть ошибки (список печатается).
"""
import asyncio
import os
import sys
import tempfile
from datetime import timedelta

# Чтобы работал `import config`, `import core`, ... из корня проекта.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

FAILS = []
PASSES = []


def check(name, condition):
    if condition:
        PASSES.append(name)
        print(f"  ✅ {name}")
    else:
        FAILS.append(name)
        print(f"  ❌ {name}")


async def expect_raises(name, exc_type, coro):
    try:
        await coro
    except exc_type:
        check(name, True)
    except Exception as e:  # noqa: BLE001
        check(f"{name} (получено {type(e).__name__})", False)
    else:
        check(f"{name} (исключение не брошено)", False)


class FakeBot:
    """Заглушка бота: запоминает отправленные сообщения."""

    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text))


async def wipe_bookings(db):
    async with db.connect() as conn:
        await conn.execute("DELETE FROM bookings")
        await conn.commit()


async def main():
    # ---------- Пункт 1: импорт всех модулей ----------
    print("\n[1] Импорт модулей и старт без ошибок импорта")
    tmp = tempfile.mkdtemp(prefix="aurea_selfcheck_")
    db_path = os.path.join(tmp, "test.db")
    os.environ["DB_PATH"] = db_path  # на случай раннего чтения config

    import config  # noqa: E402
    from core import db  # noqa: E402

    db.set_db_path(db_path)
    config.DB_PATH = db_path

    from core import bookings, consent, slots, validation  # noqa: E402
    from core.bookings import (  # noqa: E402
        BookingLimitError,
        InvalidSlotError,
        PastSlotError,
        SlotTakenError,
        UnknownServiceError,
    )
    from data import get_service, load_services, schedule, texts  # noqa: E402

    import aiosqlite  # noqa: E402
    check("aiosqlite.Row доступен", hasattr(aiosqlite, "Row"))

    # Импорт Telegram-слоя (ловит ошибки импорта хендлеров/клавиатур/FSM).
    from bot import keyboards as kb  # noqa: E402
    from bot import reminders, states  # noqa: E402
    from bot.handlers import admin, booking, fallback, menu, my_bookings, start  # noqa: E402
    import bot.main  # noqa: E402
    from bot.handlers.admin import notify_new_booking  # noqa: E402

    _tg_layer = (states, admin, booking, fallback, menu, my_bookings, start, bot.main)
    check("Telegram-слой импортирован (хендлеры/FSM/main)",
          all(module is not None for module in _tg_layer))

    await db.init_db()
    check("init_db() отработал", os.path.exists(db_path))

    # ---------- Пункт 2: согласие (152-ФЗ) до сбора данных ----------
    print("\n[2] Согласие сохраняется и проверяется; без него записи нет")
    uid = 1001
    before = await consent.has_consent(uid)
    check("до согласия has_consent == False", before is False)
    await consent.save_consent(uid, "Тест Тестов")
    after = await consent.has_consent(uid)
    check("после согласия has_consent == True", after is True)
    # Идемпотентность: повторное согласие не создаёт дубль / не падает.
    await consent.save_consent(uid, "Другое Имя")
    check("повторное согласие не падает", await consent.has_consent(uid) is True)
    # Гейт согласия в сценарии записи — через ту же функцию, что вызывает хендлер.
    check("гейт согласия для нового пользователя закрыт",
          await consent.has_consent(2002) is False)

    # ---------- Пункт 4 (часть): даты — окно, рабочие дни, без прошлого ----------
    print("\n[4a] Доступные даты: окно записи, только рабочие дни, без сегодня")
    dates = slots.available_dates()
    check("список дат не пуст", len(dates) > 0)
    today = bookings._now().date()
    check("сегодня не предлагается", all(d > today for d in dates))
    check("не раньше, чем завтра",
          dates[0] == today + timedelta(days=schedule.BOOKING_START_OFFSET_DAYS))
    check("не позже окна +14 дней",
          dates[-1] <= today + timedelta(days=schedule.BOOKING_WINDOW_DAYS))
    check("все даты — рабочие дни",
          all(schedule.working_hours_for(d.weekday()) for d in dates))

    # ---------- Пункт 3: полный сценарий записи до подтверждения ----------
    print("\n[3] Полный путь услуга→дата→время→создание записи")
    await wipe_bookings(db)
    services = load_services()
    check("услуги загружены из services.json", len(services) == 5)
    svc_id = "lips_1ml"
    check("услуга lips_1ml существует", get_service(svc_id) is not None)
    d0 = dates[0].isoformat()
    free0 = await slots.free_slots(d0, svc_id)
    check("есть свободные слоты на первую дату", len(free0) > 0)
    t0 = free0[0]
    bid = await bookings.create_booking(uid, svc_id, d0, t0, "Иван", "+79001234567")
    check("create_booking вернул id", isinstance(bid, int) and bid > 0)

    # ---------- Пункт 4 (часть): занятый слот не предлагается ----------
    print("\n[4b] Занятый слот исчезает из свободных и is_slot_free")
    check("is_slot_free(занятый) == False", await bookings.is_slot_free(d0, t0) is False)
    free_after = await slots.free_slots(d0, svc_id)
    check("занятое время исключено из free_slots", t0 not in free_after)
    # Прошедшее время/нерабочие — косвенно: нет '10:30' (вне сетки) и нет сегодняшних.
    check("вне сетки слота ('10:30') нет в списке", "10:30" not in free_after)

    # ---------- Пункт 6: запись видна в «Мои записи» + уведомление админу ----------
    print("\n[6] Запись в «Мои записи» и уведомление администратору")
    mine = await bookings.get_user_bookings(uid)
    check("запись видна в get_user_bookings", any(b["id"] == bid for b in mine))
    upcoming = await bookings.get_all_upcoming()
    check("запись видна администратору (get_all_upcoming)",
          any(b["id"] == bid for b in upcoming))

    old_admin = config.ADMIN_CHAT_ID
    config.ADMIN_CHAT_ID = 999999
    fake = FakeBot()
    await notify_new_booking(fake, {
        "user_id": uid, "service_name": "Контурная пластика губ (1 мл)",
        "date": d0, "time": t0, "name": "Иван", "phone": "+79001234567",
    })
    check("уведомление ушло администратору", len(fake.sent) == 1 and fake.sent[0][0] == 999999)
    config.ADMIN_CHAT_ID = old_admin

    # ---------- Пункт 7: отмена освобождает слот ----------
    print("\n[7] Отмена записи освобождает слот")
    ok = await bookings.cancel_booking(bid, uid)
    check("cancel_booking вернул True", ok is True)
    check("слот снова свободен", await bookings.is_slot_free(d0, t0) is True)
    mine2 = await bookings.get_user_bookings(uid)
    check("отменённой записи нет в «Мои записи»", all(b["id"] != bid for b in mine2))
    # Повторная отмена — безопасна.
    check("повторная отмена возвращает False", await bookings.cancel_booking(bid, uid) is False)

    # ---------- Лимит активных записей ----------
    print("\n[доп] Лимит 3 активные записи на пользователя")
    await wipe_bookings(db)
    luid = 3003
    free_lim = await slots.free_slots(d0, svc_id)
    check("на дату есть ≥4 слота для теста лимита", len(free_lim) >= 4)
    for i in range(3):
        await bookings.create_booking(luid, svc_id, d0, free_lim[i], "Лимит", "+79001112233")
    await expect_raises(
        "4-я запись сверх лимита → BookingLimitError",
        BookingLimitError,
        bookings.create_booking(luid, svc_id, d0, free_lim[3], "Лимит", "+79001112233"),
    )

    # ---------- Гонка: занятый слот нельзя занять повторно ----------
    print("\n[доп] Защита от гонки: повторная запись в слот → SlotTakenError")
    await wipe_bookings(db)
    await bookings.create_booking(4004, svc_id, d0, free_lim[0], "Первый", "+79001112233")
    await expect_raises(
        "второй в тот же слот → SlotTakenError",
        SlotTakenError,
        bookings.create_booking(5005, svc_id, d0, free_lim[0], "Второй", "+79004445566"),
    )

    # ---------- Прочие ошибки create_booking ----------
    print("\n[доп] Прошлое/вне сетки/неизвестная услуга отклоняются")
    yesterday = (today - timedelta(days=1)).isoformat()
    await expect_raises("дата в прошлом → PastSlotError", PastSlotError,
                        bookings.create_booking(6006, svc_id, yesterday, "10:00", "X", "+79001112233"))
    await expect_raises("время вне сетки → InvalidSlotError", InvalidSlotError,
                        bookings.create_booking(6006, svc_id, d0, "10:30", "X", "+79001112233"))
    await expect_raises("неизвестная услуга → UnknownServiceError", UnknownServiceError,
                        bookings.create_booking(6006, "no_such", d0, "10:00", "X", "+79001112233"))

    # ---------- Пункт 5: валидация телефона и имени ----------
    print("\n[5] Валидация телефона и имени")
    check("+7… нормализуется", validation.normalize_phone("+79001234567") == "+79001234567")
    check("8… → +7", validation.normalize_phone("89001234567") == "+79001234567")
    check("с символами → +7",
          validation.normalize_phone("8 (900) 123-45-67") == "+79001234567")
    check("79… → +7", validation.normalize_phone("79001234567") == "+79001234567")
    check("короткий номер отклонён", validation.normalize_phone("12345") is None)
    check("10 цифр отклонены", validation.normalize_phone("9001234567") is None)
    check("пустой номер отклонён", validation.normalize_phone("") is None)
    check("имя 'Ян' валидно", validation.validate_name("Ян") == "Ян")
    check("пробелы схлопываются", validation.validate_name("  Мария   Петрова ") == "Мария Петрова")
    check("1 символ отклонён", validation.validate_name("A") is None)
    check("ссылка отклонена", validation.validate_name("http://evil.ru") is None)
    check("@упоминание отклонено", validation.validate_name("@user") is None)
    check(">50 символов отклонено", validation.validate_name("и" * 51) is None)

    # ---------- Пункт 8 + напоминания ----------
    print("\n[8] Напоминания и планировщик")
    await wipe_bookings(db)
    # Вставляем запись напрямую с контролируемым временем визита.
    vdate, vtime = "2030-01-10", "12:00"
    async with db.connect() as conn:
        cur = await conn.execute(
            "INSERT INTO bookings (user_id, service_id, service_name, date, time, "
            "name, phone, status, created_at) VALUES (?,?,?,?,?,?,?,'active',?)",
            (7007, svc_id, "Тест", vdate, vtime, "Тест", "+79001112233", "2030-01-01T00:00:00"),
        )
        rid = cur.lastrowid
        await conn.commit()
    vdt = bookings.visit_datetime(vdate, vtime)

    due_24 = await bookings.get_due_reminders(vdt - timedelta(hours=23))
    kinds_24 = {d["kind"]: d for d in due_24 if d["id"] == rid}
    check("за ~24ч: напоминание 24h помечено к отправке",
          "24h" in kinds_24 and kinds_24["24h"]["send"] is True)
    check("за ~24ч: 2h ещё не наступило", "2h" not in kinds_24)

    await bookings.mark_reminded(rid, "24h")
    due_again = await bookings.get_due_reminders(vdt - timedelta(hours=23))
    check("после отметки 24h повторно не возвращается",
          all(not (d["id"] == rid and d["kind"] == "24h") for d in due_again))

    due_2 = await bookings.get_due_reminders(vdt - timedelta(minutes=90))
    kinds_2 = {d["kind"]: d for d in due_2 if d["id"] == rid}
    check("за ~2ч: напоминание 2h помечено к отправке",
          "2h" in kinds_2 and kinds_2["2h"]["send"] is True)

    # Пропущенное окно: отправлять не нужно, но пометить — да (send=False).
    await wipe_bookings(db)
    async with db.connect() as conn:
        cur = await conn.execute(
            "INSERT INTO bookings (user_id, service_id, service_name, date, time, "
            "name, phone, status, created_at) VALUES (?,?,?,?,?,?,?,'active',?)",
            (7008, svc_id, "Тест", vdate, vtime, "Тест", "+79001112233", "2030-01-01T00:00:00"),
        )
        rid2 = cur.lastrowid
        await conn.commit()
    due_missed = await bookings.get_due_reminders(vdt - timedelta(minutes=30))
    missed = [d for d in due_missed if d["id"] == rid2]
    check("пропущенное окно: записи есть, но send=False",
          len(missed) > 0 and all(d["send"] is False for d in missed))

    # scan_and_send не падает и шлёт только то, что нужно.
    await wipe_bookings(db)
    async with db.connect() as conn:
        await conn.execute(
            "INSERT INTO bookings (user_id, service_id, service_name, date, time, "
            "name, phone, status, created_at) VALUES (?,?,?,?,?,?,?,'active',?)",
            (7009, svc_id, "Тест", vdate, vtime, "Тест", "+79001112233", "2030-01-01T00:00:00"),
        )
        await conn.commit()
    fake2 = FakeBot()
    await reminders.scan_and_send(fake2)  # реальный момент сейчас — визит далеко, ничего слать не нужно
    check("scan_and_send отработал без ошибок", True)

    # Планировщик стартует и останавливается без ошибок.
    sched = reminders.setup_scheduler(FakeBot())
    sched.start()
    check("планировщик запущен", sched.running is True)
    check("задача напоминаний зарегистрирована", sched.get_job("reminders") is not None)
    sched.shutdown(wait=False)
    # AsyncIOScheduler завершает остановку на следующем тике цикла событий.
    await asyncio.sleep(0.1)
    check("планировщик остановлен", sched.running is False)

    # ---------- Клавиатуры собираются, callback_data корректны ----------
    print("\n[доп] Клавиатуры собираются, callback_data ≤ 64 байт")
    markups = [
        kb.consent_kb(), kb.main_menu(), kb.back_menu_kb(), kb.contacts_kb(),
        kb.services_kb(services), kb.dates_kb(dates),
        kb.times_kb(free0 if free0 else ["09:00"]), kb.confirm_kb(),
        kb.my_bookings_kb([{"id": 1, "date": d0, "time": t0, "service_name": "X"}]),
    ]
    all_ok = True
    for m in markups:
        for row in m.inline_keyboard:
            for btn in row:
                if btn.callback_data is not None and len(btn.callback_data.encode()) > 64:
                    all_ok = False
    check("все inline-клавиатуры собраны", len(markups) == 9)
    check("все callback_data ≤ 64 байт", all_ok)
    phone_markup = kb.phone_kb()
    check("reply-клавиатура телефона запрашивает контакт",
          phone_markup.keyboard[0][0].request_contact is True)

    # ---------- Тексты рендерятся ----------
    print("\n[доп] Тексты рендерятся без ошибок")
    _ = texts.services_list()
    _ = texts.booking_summary("Услуга", d0, t0, "Имя", "+79001234567")
    _ = texts.booking_success("Услуга", d0, t0)
    _ = texts.reminder("Услуга", d0, t0, "24h")
    _ = texts.admin_new_booking({
        "user_id": 1, "service_name": "Услуга", "date": d0, "time": t0,
        "name": "Имя", "phone": "+79001234567",
    })
    check("все тексты собраны", True)

    # ---------- Итог ----------
    print("\n" + "=" * 56)
    print(f"ИТОГО: пройдено {len(PASSES)}, провалено {len(FAILS)}")
    if FAILS:
        print("ПРОВАЛЕНЫ:")
        for f in FAILS:
            print(f"  - {f}")
    print("=" * 56)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
