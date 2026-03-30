from __future__ import annotations

from calendar import monthrange
from datetime import date

from app.database.models import RepeatType


def parse_user_date(raw: str) -> date:
    parts = raw.split(".")
    if len(parts) != 3:
        raise ValueError("Неверный формат даты")
    day, month, year = map(int, parts)
    return date(year=year, month=month, day=day)


def clamp_day(year: int, month: int, desired_day: int) -> int:
    return min(desired_day, monthrange(year, month)[1])


def _next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def get_next_occurrence(event_date: date, repeat_type: RepeatType, from_date: date) -> date:
    threshold = max(event_date, from_date)

    if repeat_type == RepeatType.DAILY:
        return threshold

    if repeat_type == RepeatType.MONTHLY:
        year = threshold.year
        month = threshold.month
        day = clamp_day(year, month, event_date.day)
        candidate = date(year=year, month=month, day=day)
        if candidate < threshold:
            year, month = _next_month(year, month)
            day = clamp_day(year, month, event_date.day)
            candidate = date(year=year, month=month, day=day)
        return candidate

    if repeat_type == RepeatType.YEARLY:
        year = threshold.year
        day = clamp_day(year, event_date.month, event_date.day)
        candidate = date(year=year, month=event_date.month, day=day)
        if candidate < threshold:
            year += 1
            day = clamp_day(year, event_date.month, event_date.day)
            candidate = date(year=year, month=event_date.month, day=day)
        return candidate

    raise ValueError(f"Неизвестный тип повторения: {repeat_type}")
