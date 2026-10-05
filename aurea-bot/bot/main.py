"""Точка входа: инициализация БД, запуск long polling и планировщика."""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
from bot.handlers import admin, booking, fallback, menu, my_bookings, start
from bot.reminders import setup_scheduler
from core import db

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # Проверяем обязательные параметры .env.
    config.validate()

    # Готовим БД.
    await db.init_db()

    bot = Bot(
        config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Порядок важен: start первым (чтобы /start всегда работал),
    # fallback — последним (ловит устаревшие кнопки и прочее).
    for module in (start, menu, booking, my_bookings, admin, fallback):
        dp.include_router(module.router)

    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Планировщик напоминаний запущен")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Запуск long polling…")
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Выход")
    except RuntimeError as exc:
        # Понятное сообщение вместо трейсбэка при незаполненном .env.
        print(f"Ошибка запуска: {exc}")
        print("Заполните .env (см. .env.example) и запустите снова.")
        sys.exit(1)
