"""Валидация и нормализация пользовательского ввода (телефон, имя).

Чистые функции без зависимостей от aiogram — пригодны и для HTTP API.
"""
import re

_NON_DIGIT = re.compile(r"\D")
# Запрещаем ссылки и упоминания в имени.
_NAME_FORBIDDEN = re.compile(r"(https?://|www\.|t\.me|@)", re.IGNORECASE)


def normalize_phone(raw: str | None) -> str | None:
    """РФ-номер → '+7XXXXXXXXXX'. None, если формат неверный.

    Принимает +7XXXXXXXXXX, 8XXXXXXXXXX, с пробелами/скобками/дефисами —
    всё нецифровое отбрасывается. Требуется ровно 11 цифр, начинается с 7 или 8.
    """
    if not raw:
        return None
    digits = _NON_DIGIT.sub("", raw)
    if len(digits) == 11 and digits[0] in ("7", "8"):
        return "+7" + digits[1:]
    return None


def validate_name(raw: str | None) -> str | None:
    """Нормализованное имя (2–50 символов, без ссылок/@). None, если невалидно."""
    if not raw:
        return None
    name = " ".join(raw.split()).strip()
    if len(name) < 2 or len(name) > 50:
        return None
    if _NAME_FORBIDDEN.search(name):
        return None
    return name
