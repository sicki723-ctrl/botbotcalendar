from __future__ import annotations

from datetime import datetime, date
from zoneinfo import ZoneInfo

from app.database.models import Event, RepeatType, User
from app.database.repositories import EventRepository, UserRepository
from app.utils.date_utils import get_next_occurrence


class EventService:
    def __init__(self, user_repo: UserRepository, event_repo: EventRepository, timezone_name: str) -> None:
        self._user_repo = user_repo
        self._event_repo = event_repo
        self._timezone_name = timezone_name

    @property
    def timezone_name(self) -> str:
        return self._timezone_name

    async def ensure_user(self, telegram_id: int) -> User:
        return await self._user_repo.get_or_create(telegram_id)

    async def create_event(
        self,
        telegram_id: int,
        title: str,
        event_date_iso: str,
        repeat_type: RepeatType,
        remind_before_days: int,
        reminders_per_day: int,
    ) -> int:
        user = await self._user_repo.get_or_create(telegram_id)
        return await self._event_repo.create(
            user_id=user.id,
            title=title,
            event_date_iso=event_date_iso,
            repeat_type=repeat_type,
            remind_before_days=remind_before_days,
            reminders_per_day=reminders_per_day,
        )

    async def list_events_for_user(self, telegram_id: int) -> list[tuple[Event, date]]:
        events = await self._event_repo.list_by_telegram_id(telegram_id)
        today = datetime.now(ZoneInfo(self._timezone_name)).date()
        result: list[tuple[Event, date]] = []
        for event in events:
            next_occurrence = get_next_occurrence(event.event_date, event.repeat_type, today)
            result.append((event, next_occurrence))
        return result

    async def get_event_for_user(self, telegram_id: int, event_id: int) -> tuple[Event, date] | None:
        event = await self._event_repo.get_by_id_for_telegram_user(event_id, telegram_id)
        if event is None:
            return None
        today = datetime.now(ZoneInfo(self._timezone_name)).date()
        next_occurrence = get_next_occurrence(event.event_date, event.repeat_type, today)
        return event, next_occurrence

    async def update_event_field(
        self,
        telegram_id: int,
        event_id: int,
        field_name: str,
        value: str | int,
    ) -> bool:
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            return False
        return await self._event_repo.update_field(event_id=event_id, user_id=user.id, field=field_name, value=value)

    async def delete_event(self, telegram_id: int, event_id: int) -> bool:
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            return False
        return await self._event_repo.soft_delete(event_id=event_id, user_id=user.id)
