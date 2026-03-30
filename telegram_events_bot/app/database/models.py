from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

import aiosqlite


class RepeatType(str, Enum):
    DAILY = "daily"
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass(slots=True)
class User:
    id: int
    telegram_id: int
    created_at: str

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "User":
        return cls(
            id=row["id"],
            telegram_id=row["telegram_id"],
            created_at=row["created_at"],
        )


@dataclass(slots=True)
class Event:
    id: int
    user_id: int
    title: str
    event_date: date
    repeat_type: RepeatType
    remind_before_days: int
    reminders_per_day: int
    is_active: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "Event":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            event_date=date.fromisoformat(row["event_date"]),
            repeat_type=RepeatType(row["repeat_type"]),
            remind_before_days=row["remind_before_days"],
            reminders_per_day=row["reminders_per_day"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass(slots=True)
class ReminderEvent(Event):
    telegram_id: int

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "ReminderEvent":
        base = Event.from_row(row)
        return cls(
            id=base.id,
            user_id=base.user_id,
            title=base.title,
            event_date=base.event_date,
            repeat_type=base.repeat_type,
            remind_before_days=base.remind_before_days,
            reminders_per_day=base.reminders_per_day,
            is_active=base.is_active,
            created_at=base.created_at,
            updated_at=base.updated_at,
            telegram_id=row["telegram_id"],
        )
