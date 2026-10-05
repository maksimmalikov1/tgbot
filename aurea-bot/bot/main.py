"""Точка входа: инициализация БД, запуск long polling и планировщика."""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

import config
from bot.handlers import admin, booking, fallback, menu, my_bookings, start
from bot.reminders import setup_scheduler
from core import db

logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot) -> None:
    """Устанавливает меню команд: публичное и расширенное для администратора."""
    try:
        await bot.set_my_commands(
            [BotCommand(command="start", description="Начать / главное меню")],
            scope=BotCommandScopeDefault(),
        )
        if config.ADMIN_CHAT_ID is not None:
            await bot.set_my_commands(
                [
                    BotCommand(command="start", description="Начать / главное меню"),
                    BotCommand(command="bookings", description="Все предстоящие записи"),
                    BotCommand(command="test_reminder", description="Тестовое напоминание"),
                    BotCommand(command="id", description="Показать мой chat_id"),
                ],
                scope=BotCommandScopeChat(chat_id=config.ADMIN_CHAT_ID),
            )
    except Exception:  # noqa: BLE001 — сбой установки команд не должен мешать старту
        logger.exception("Не удалось установить команды бота")


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
        await set_bot_commands(bot)
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
