"""Планировщик напоминаний (APScheduler).

Раз в минуту сканирует активные записи и отправляет напоминания за 24 ч и 2 ч
до визита. Устойчив к перезапуску: отметки об отправке хранятся в БД, поэтому
повторных напоминаний не будет, а пропущенные из-за простоя обрабатываются
корректно (см. core.bookings.get_due_reminders).
"""
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TZ
from core import bookings
from data import texts

logger = logging.getLogger(__name__)


async def scan_and_send(bot) -> None:
    """Один проход: найти и обработать напоминания, которые пора отправить."""
    try:
        due = await bookings.get_due_reminders(datetime.now(TZ))
    except Exception:  # noqa: BLE001 — сбой скана не должен ронять планировщик
        logger.exception("Не удалось получить список напоминаний")
        return

    for item in due:
        if item["send"]:
            try:
                await bot.send_message(
                    item["user_id"],
                    texts.reminder(
                        item["service_name"], item["date"], item["time"], item["kind"]
                    ),
                )
            except Exception:  # noqa: BLE001 — клиент мог заблокировать бота и т.п.
                logger.exception(
                    "Не удалось отправить напоминание (booking id=%s)", item["id"]
                )
        # Помечаем как обработанное в любом случае (в т.ч. пропущенное окно),
        # чтобы не слать повторно.
        try:
            await bookings.mark_reminded(item["id"], item["kind"])
        except Exception:  # noqa: BLE001
            logger.exception(
                "Не удалось отметить напоминание (booking id=%s)", item["id"]
            )


def setup_scheduler(bot) -> AsyncIOScheduler:
    """Создаёт и настраивает планировщик (без запуска)."""
    scheduler = AsyncIOScheduler(timezone=str(TZ))
    scheduler.add_job(
        scan_and_send,
        trigger="interval",
        seconds=60,
        args=[bot],
        id="reminders",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    return scheduler
