# Подключение к реальному боту и запуск

Пошагово: как создать бота, как его назвать, где взять токены и как запустить —
сначала для теста (на своём компьютере), потом на сервере 24/7.

---

## Шаг 1. Создать бота и получить BOT_TOKEN

1. Открой в Telegram [@BotFather](https://t.me/BotFather) → отправь `/newbot`.
2. **Имя бота** (видят клиенты, можно с пробелами и кириллицей). Например:
   - `Aurea — запись на приём`
   - `Aurea | Эстетическая косметология`
3. **Username** (технический логин, латиница, обязан заканчиваться на `bot`,
   должен быть свободен). Например (проверь, какой свободен):
   - `aurea_clinic_bot`
   - `aurea_beauty_bot`
   - `aurea_msk_bot`
4. В ответ BotFather пришлёт **токен** вида
   `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` — это `BOT_TOKEN`.
   Храни его в секрете: токен = полный доступ к боту.

Необязательно, но желательно оформить профиль бота там же, у BotFather:
- `/setdescription` — текст на пустом экране до старта («Онлайн-запись в клинику
  эстетической косметологии Aurea. Нажмите «Запустить».»).
- `/setabouttext` — краткое «о боте».
- `/setuserpic` — аватар (логотип Aurea).

> Меню команд (`/start` и т.д.) настраивать вручную **не нужно** — бот сам
> выставляет его при старте (`set_bot_commands`).

---

## Шаг 2. Узнать ADMIN_CHAT_ID

Это числовой id чата, куда приходят уведомления о новых записях (твой личный).

**Самый простой способ — через самого бота:**
1. Запусти бота хотя бы раз (Шаг 4) — даже с незаполненным `ADMIN_CHAT_ID`.
2. Напиши своему боту в личку `/id` — он ответит твоим `chat_id`.
3. Впиши это число в `.env` и перезапусти бота.

Альтернатива: написать [@userinfobot](https://t.me/userinfobot) — он пришлёт твой id.

---

## Шаг 3. Заполнить .env

```bash
cp .env.example .env
```

Открой `.env` и заполни:

```ini
BOT_TOKEN=123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ADMIN_CHAT_ID=123456789
TIMEZONE=Europe/Moscow
POLICY_URL=https://твой-сайт/policy
CONSENT_URL=https://твой-сайт/consent
```

- `BOT_TOKEN` — из Шага 1.
- `ADMIN_CHAT_ID` — из Шага 2 (просто число, без кавычек).
- `POLICY_URL` / `CONSENT_URL` — см. Шаг 5. Для теста можно оставить как есть.

`.env` в git не попадает (он в `.gitignore`) — так и должно быть.

---

## Шаг 4. Быстрый запуск для теста (на своём компьютере)

Боту **не нужен** домен, белый IP или webhook — он работает через long polling
(только исходящие соединения). Поэтому для проверки хватит обычного ноутбука.

```bash
cd aurea-bot
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m bot.main
```

В логах появится «Запуск long polling…». Открой бота в Telegram, нажми
«Запустить» / `/start` — должен прийти экран согласия. Останавливается Ctrl+C.

> Пока запущено на ноутбуке — бот онлайн. Закрыл терминал/уснул ноут — бот
> офлайн. Для постоянной работы см. Шаг 6.

---

## Шаг 5. Юридические ссылки (152-ФЗ) перед реальными клиентами

Бот на экране согласия даёт две кнопки — на `POLICY_URL` (политика
конфиденциальности) и `CONSENT_URL` (согласие на обработку ПДн). Перед тем как
пускать реальных людей:

1. Размести два документа по доступным ссылкам (можно на своём сайте, напр.
   на той же площадке, где лежит сайт клиники).
2. Пропиши реальные `POLICY_URL` и `CONSENT_URL` в `.env`.
3. Замени демо-реквизиты в `data/clinic.py` (телефон `+7 (900) 000-00-00`,
   email `hello@aurea.ru`) на настоящие.
4. Размести бота на **сервере в РФ** (локализация персональных данных).

---

## Шаг 6. Боевой запуск 24/7 на сервере в РФ

Нужен VPS у российского хостера (Timeweb, Reg.ru, Selectel, VK Cloud и т.п.),
Ubuntu/Debian. Дальше — один раз настроить, и бот сам поднимается после
перезагрузки и падений.

```bash
# 1) Пользователь и каталог
sudo useradd -r -m -d /opt/aurea-bot aurea
sudo mkdir -p /opt/aurea-bot

# 2) Код проекта в /opt/aurea-bot (через git или scp). Например:
sudo git clone <URL-репозитория> /tmp/repo
sudo cp -r /tmp/repo/aurea-bot/. /opt/aurea-bot/
sudo chown -R aurea:aurea /opt/aurea-bot

# 3) Виртуальное окружение и зависимости
sudo -u aurea python3 -m venv /opt/aurea-bot/.venv
sudo -u aurea /opt/aurea-bot/.venv/bin/pip install -r /opt/aurea-bot/requirements.txt

# 4) .env (впиши BOT_TOKEN, ADMIN_CHAT_ID, реальные ссылки)
sudo -u aurea cp /opt/aurea-bot/.env.example /opt/aurea-bot/.env
sudo -u aurea nano /opt/aurea-bot/.env

# 5) Служба systemd (файл в репозитории: deploy/aurea-bot.service)
sudo cp /opt/aurea-bot/deploy/aurea-bot.service /etc/systemd/system/aurea-bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now aurea-bot
```

Управление:

```bash
sudo systemctl status aurea-bot      # статус
journalctl -u aurea-bot -f           # живые логи
sudo systemctl restart aurea-bot     # перезапуск (после правок .env/кода)
sudo systemctl stop aurea-bot        # остановить
```

> Часовой пояс сервера роли не играет — бот считает время по `TIMEZONE` из
> `.env` (по умолчанию `Europe/Moscow`).

---

## Шаг 7. Проверка, что всё работает

1. `/start` → приходит приветствие и экран согласия; без «Соглашаюсь» дальше нельзя.
2. «📅 Записаться» → услуга → дата → время → имя → телефон → подтверждение.
3. После подтверждения: клиенту — подтверждение, тебе (ADMIN_CHAT_ID) —
   уведомление о записи.
4. `/bookings` (от админа) → список предстоящих записей.
5. `/test_reminder` (от админа) → приходит пример напоминания.
6. «📋 Мои записи» → отмена освобождает слот.

Автономная самопроверка кода (без токена и сети):

```bash
python tests/selfcheck.py
```

---

## Частые вопросы

- **«Бот не отвечает».** Проверь, что процесс запущен (`systemctl status` или
  терминал открыт), `BOT_TOKEN` верный, есть интернет. Один бот = один
  запущенный процесс (нельзя гонять и локально, и на сервере одновременно —
  будет конфликт long polling).
- **«Не приходят уведомления о записях».** Не задан/неверный `ADMIN_CHAT_ID`,
  либо ты не нажимал `/start` своему боту (Telegram не даёт писать первым).
  Напиши боту `/id`, впиши число, перезапусти.
- **«Как поменять цены/тексты/расписание».** Правь файлы в `data/`
  (`services.json`, `texts.py`, `schedule.py`, `clinic.py`) и перезапусти бота.
