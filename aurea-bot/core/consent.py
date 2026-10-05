"""Сохранение и проверка согласия на обработку персональных данных (152-ФЗ).

Фиксируем факт согласия: user_id, имя в Telegram, дата-время (первое согласие).
Не зависит от aiogram.
"""
from datetime import datetime

from config import TZ
from core import db


async def has_consent(user_id: int) -> bool:
    """True, если пользователь уже дал согласие."""
    async with db.connect() as conn:
        cur = await conn.execute(
            "SELECT 1 FROM consents WHERE user_id = ? LIMIT 1", (user_id,)
        )
        row = await cur.fetchone()
    return row is not None


async def save_consent(user_id: int, tg_name: str | None) -> None:
    """Сохраняет факт согласия. Первое согласие не перезаписывается (OR IGNORE)."""
    created_at = datetime.now(TZ).isoformat()
    async with db.connect() as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO consents (user_id, tg_name, created_at) "
            "VALUES (?, ?, ?)",
            (user_id, tg_name, created_at),
        )
        await conn.commit()
