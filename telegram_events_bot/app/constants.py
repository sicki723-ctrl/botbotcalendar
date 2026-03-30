from __future__ import annotations

from app.database.models import RepeatType


MAX_TITLE_LENGTH = 120
REMIND_BEFORE_DAYS_OPTIONS = [0, 1, 2, 3, 5, 7, 14, 30]
REMINDERS_PER_DAY_OPTIONS = [1, 2, 3]

MAIN_MENU_ADD = "Добавить мероприятие"
MAIN_MENU_LIST = "Мои мероприятия"
MAIN_MENU_HELP = "Помощь"

REPEAT_RU_LABELS: dict[RepeatType, str] = {
    RepeatType.DAILY: "Каждый день",
    RepeatType.MONTHLY: "Каждый месяц",
    RepeatType.YEARLY: "Каждый год",
}
