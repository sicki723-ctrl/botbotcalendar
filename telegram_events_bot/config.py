from __future__ import annotations

from dataclasses import dataclass
from datetime import time
import os

from dotenv import load_dotenv


def _parse_time(value: str) -> time:
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError(f"Неверный формат времени: {value}. Ожидается HH:MM")
    hour = int(parts[0])
    minute = int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Неверное время: {value}")
    return time(hour=hour, minute=minute)


@dataclass(slots=True)
class Config:
    bot_token: str
    db_path: str
    timezone: str
    morning_time: time
    day_time: time
    evening_time: time

    @property
    def reminder_times(self) -> list[time]:
        return [self.morning_time, self.day_time, self.evening_time]


def load_config() -> Config:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError("Переменная BOT_TOKEN не задана")

    db_path = os.getenv("DB_PATH", "data/bot.db").strip()
    timezone = os.getenv("BOT_TIMEZONE", "Asia/Yekaterinburg").strip()

    morning_time = _parse_time(os.getenv("REMINDER_MORNING_TIME", "09:00").strip())
    day_time = _parse_time(os.getenv("REMINDER_DAY_TIME", "14:00").strip())
    evening_time = _parse_time(os.getenv("REMINDER_EVENING_TIME", "19:00").strip())

    return Config(
        bot_token=bot_token,
        db_path=db_path,
        timezone=timezone,
        morning_time=morning_time,
        day_time=day_time,
        evening_time=evening_time,
    )
