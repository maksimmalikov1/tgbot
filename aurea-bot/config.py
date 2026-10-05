"""Чтение .env и общие константы проекта.

Импорт этого модуля безопасен без заполненного .env (нужно для тестов и
самопроверки): значения читаются, но не валидируются. Строгую проверку
обязательных параметров выполняет validate() — её вызывает точка входа бота.
"""
import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

# Абсолютный путь к корню проекта (папка, где лежит этот файл).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Грузим .env из корня проекта (если есть).
load_dotenv(os.path.join(BASE_DIR, ".env"))

# --- Обязательные параметры ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

_admin_raw = os.getenv("ADMIN_CHAT_ID", "").strip()
try:
    ADMIN_CHAT_ID = int(_admin_raw) if _admin_raw else None
except ValueError:
    ADMIN_CHAT_ID = None

# --- Таймзона ---
TIMEZONE = (os.getenv("TIMEZONE", "Europe/Moscow").strip() or "Europe/Moscow")
try:
    TZ = ZoneInfo(TIMEZONE)
except Exception:  # noqa: BLE001 — некорректная TZ не должна ронять импорт
    TIMEZONE = "Europe/Moscow"
    TZ = ZoneInfo("Europe/Moscow")

# --- Ссылки на юридические документы (ДЕМО по умолчанию) ---
POLICY_URL = (os.getenv("POLICY_URL", "https://aurea-lips.netlify.app/").strip()
              or "https://aurea-lips.netlify.app/")
CONSENT_URL = (os.getenv("CONSENT_URL", "https://aurea-lips.netlify.app/").strip()
               or "https://aurea-lips.netlify.app/")

# --- Пути к файлам ---
_db_raw = os.getenv("DB_PATH", "").strip()
DB_PATH = _db_raw if _db_raw else os.path.join(BASE_DIR, "bot.db")

SERVICES_PATH = os.path.join(BASE_DIR, "data", "services.json")


def validate() -> None:
    """Проверяет обязательные параметры. Вызывается при старте бота.

    Бросает RuntimeError со списком проблем, если чего-то не хватает.
    """
    errors = []
    if not BOT_TOKEN:
        errors.append("BOT_TOKEN не задан в .env")
    if ADMIN_CHAT_ID is None:
        errors.append("ADMIN_CHAT_ID не задан или не является числом в .env")
    if errors:
        raise RuntimeError("Ошибки конфигурации: " + "; ".join(errors))
