from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.reminder_service import ReminderService


logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, reminder_service: ReminderService, timezone_name: str) -> None:
        self._reminder_service = reminder_service
        self._scheduler = AsyncIOScheduler(timezone=ZoneInfo(timezone_name))
        self._started = False

    def start(self) -> None:
        if self._started:
            return

        self._scheduler.add_job(
            self._reminder_service.process_due_reminders,
            trigger="cron",
            second=0,
            id="process_due_reminders",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=30,
        )
        self._scheduler.start()
        self._started = True
        logger.info("Планировщик напоминаний запущен")

    def shutdown(self) -> None:
        if not self._started:
            return
        self._scheduler.shutdown(wait=False)
        self._started = False
        logger.info("Планировщик напоминаний остановлен")
