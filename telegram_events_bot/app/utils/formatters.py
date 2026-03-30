from __future__ import annotations

from datetime import date

from app.database.models import Event, RepeatType


def build_event_draft_text(data: dict, labels: dict[RepeatType, str]) -> str:
    repeat_type = RepeatType(data["repeat_type"])
    date_iso = data["event_date"]
    year, month, day = date_iso.split("-")

    return (
        "Проверьте данные перед сохранением:\n\n"
        f"Название: <b>{data['title']}</b>\n"
        f"Дата: <b>{day}.{month}.{year}</b>\n"
        f"Повторение: <b>{labels[repeat_type]}</b>\n"
        f"Начать напоминания: <b>за {data['remind_before_days']} дн.</b>\n"
        f"Напоминаний в день: <b>{data['reminders_per_day']}</b>"
    )


def build_event_details_text(event: Event, next_occurrence: date, labels: dict[RepeatType, str]) -> str:
    return (
        "Детали мероприятия:\n\n"
        f"ID: <b>{event.id}</b>\n"
        f"Название: <b>{event.title}</b>\n"
        f"Исходная дата: <b>{event.event_date.strftime('%d.%m.%Y')}</b>\n"
        f"Следующая дата: <b>{next_occurrence.strftime('%d.%m.%Y')}</b>\n"
        f"Повторение: <b>{labels[event.repeat_type]}</b>\n"
        f"Напоминать за: <b>{event.remind_before_days} дн.</b>\n"
        f"Напоминаний в день: <b>{event.reminders_per_day}</b>"
    )
