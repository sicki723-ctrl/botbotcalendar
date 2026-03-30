from __future__ import annotations

from datetime import datetime, date, timedelta, time
import logging
from zoneinfo import ZoneInfo

from aiogram import Bot

from app.constants import REPEAT_RU_LABELS
from app.database.models import ReminderEvent
from app.database.repositories import EventRepository, NotificationLogRepository
from app.utils.date_utils import get_next_occurrence


logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(
        self,
        bot: Bot,
        event_repo: EventRepository,
        notification_repo: NotificationLogRepository,
        timezone_name: str,
        reminder_times: list[time],
    ) -> None:
        self._bot = bot
        self._event_repo = event_repo
        self._notification_repo = notification_repo
        self._tz = ZoneInfo(timezone_name)
        self._reminder_times = reminder_times

    @staticmethod
    def _pick_times(reminders_per_day: int, all_times: list[time]) -> list[time]:
        if reminders_per_day <= 1:
            return [all_times[0]]
        if reminders_per_day == 2:
            return [all_times[0], all_times[2]]
        return [all_times[0], all_times[1], all_times[2]]

    async def process_due_reminders(self) -> None:
        now = datetime.now(self._tz).replace(second=0, microsecond=0)
        today = now.date()

        try:
            events = await self._event_repo.list_active_for_reminders()
        except Exception:
            logger.exception("Ошибка чтения активных событий для напоминаний")
            return

        for event in events:
            try:
                await self._process_event(now, today, event)
            except Exception:
                logger.exception("Ошибка обработки события event_id=%s", event.id)

    async def _process_event(self, now: datetime, today: date, event: ReminderEvent) -> None:
        next_occurrence = get_next_occurrence(event.event_date, event.repeat_type, today)
        reminder_start = next_occurrence - timedelta(days=event.remind_before_days)

        if not (reminder_start <= today <= next_occurrence):
            return

        allowed_times = self._pick_times(event.reminders_per_day, self._reminder_times)
        current_time = now.time()

        for allowed_time in allowed_times:
            if current_time.hour == allowed_time.hour and current_time.minute == allowed_time.minute:
                scheduled_for = datetime.combine(today, allowed_time, tzinfo=self._tz)
                scheduled_for_iso = scheduled_for.isoformat()

                already_sent = await self._notification_repo.exists(
                    event_id=event.id,
                    user_id=event.user_id,
                    scheduled_for_iso=scheduled_for_iso,
                )
                if already_sent:
                    return

                await self._send_notification(event, next_occurrence)
                await self._notification_repo.add(
                    event_id=event.id,
                    user_id=event.user_id,
                    scheduled_for_iso=scheduled_for_iso,
                )
                return

    async def _send_notification(self, event: ReminderEvent, next_occurrence: date) -> None:
        today = datetime.now(self._tz).date()
        days_left = (next_occurrence - today).days
        if days_left == 0:
            days_text = "Событие сегодня."
        else:
            days_text = f"До события осталось: {days_left} дн."

        text = (
            "Напоминание о мероприятии\n\n"
            f"Название: <b>{event.title}</b>\n"
            f"Дата события: <b>{next_occurrence.strftime('%d.%m.%Y')}</b>\n"
            f"Повторение: <b>{REPEAT_RU_LABELS[event.repeat_type]}</b>\n"
            f"{days_text}"
        )

        await self._bot.send_message(chat_id=event.telegram_id, text=text)
