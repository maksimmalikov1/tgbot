"""Схема SQLite и подключение к БД.

Все операции открывают короткоживущее соединение через connect(). Для
низкой нагрузки записи это надёжно и просто (нет общего мутабельного стейта).
Путь к БД можно переопределить set_db_path() — используется в тестах.
"""
import aiosqlite

import config

# Текущий путь к файлу БД. Тесты могут переопределить через set_db_path().
DB_PATH = config.DB_PATH

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS consents (
    user_id    INTEGER PRIMARY KEY,
    tg_name    TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    service_id   TEXT NOT NULL,
    service_name TEXT NOT NULL,
    date         TEXT NOT NULL,          -- YYYY-MM-DD
    time         TEXT NOT NULL,          -- HH:MM
    name         TEXT NOT NULL,
    phone        TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active',  -- active | cancelled
    created_at   TEXT NOT NULL,
    reminded_24h INTEGER NOT NULL DEFAULT 0,
    reminded_2h  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id, status);
CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(date, status);

-- Защита от гонки: в один слот не более одной активной записи.
CREATE UNIQUE INDEX IF NOT EXISTS uniq_active_slot
    ON bookings(date, time) WHERE status = 'active';
"""


def set_db_path(path: str) -> None:
    """Переопределяет путь к БД (для тестов)."""
    global DB_PATH
    DB_PATH = path


def connect():
    """Возвращает контекст-менеджер соединения aiosqlite к текущему DB_PATH."""
    return aiosqlite.connect(DB_PATH)


async def init_db() -> None:
    """Создаёт таблицы и индексы, если их ещё нет."""
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.executescript(SCHEMA)
        await conn.commit()
