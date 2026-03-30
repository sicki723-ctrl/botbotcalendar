from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import load_config
from app.database.db import Database
from app.database.repositories import EventRepository, NotificationLogRepository, UserRepository
from app.handlers.common import get_common_router
from app.handlers.events import get_events_router
from app.scheduler.scheduler import SchedulerService
from app.services.event_service import EventService
from app.services.reminder_service import ReminderService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    config = load_config()

    db_path = Path(config.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db = Database(config.db_path)
    await db.connect()
    await db.init_schema()

    user_repo = UserRepository(db)
    event_repo = EventRepository(db)
    notification_repo = NotificationLogRepository(db)

    event_service = EventService(
        user_repo=user_repo,
        event_repo=event_repo,
        timezone_name=config.timezone,
    )

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    reminder_service = ReminderService(
        bot=bot,
        event_repo=event_repo,
        notification_repo=notification_repo,
        timezone_name=config.timezone,
        reminder_times=config.reminder_times,
    )
    scheduler_service = SchedulerService(reminder_service=reminder_service, timezone_name=config.timezone)

    dp = Dispatcher()
    dp.include_router(get_common_router(event_service))
    dp.include_router(get_events_router(event_service))

    scheduler_service.start()

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler_service.shutdown()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
