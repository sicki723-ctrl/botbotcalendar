from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.constants import REMIND_BEFORE_DAYS_OPTIONS, REMINDERS_PER_DAY_OPTIONS
from app.database.models import RepeatType


def repeat_type_keyboard(prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Каждый день", callback_data=f"{prefix}:{RepeatType.DAILY.value}")
    builder.button(text="Каждый месяц", callback_data=f"{prefix}:{RepeatType.MONTHLY.value}")
    builder.button(text="Каждый год", callback_data=f"{prefix}:{RepeatType.YEARLY.value}")
    builder.adjust(1)
    return builder.as_markup()


def remind_before_days_keyboard(prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for days in REMIND_BEFORE_DAYS_OPTIONS:
        title = "В день события" if days == 0 else f"За {days} дн."
        builder.button(text=title, callback_data=f"{prefix}:{days}")
    builder.adjust(3, 3, 2)
    return builder.as_markup()


def reminders_per_day_keyboard(prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for count in REMINDERS_PER_DAY_OPTIONS:
        builder.button(text=str(count), callback_data=f"{prefix}:{count}")
    builder.adjust(3)
    return builder.as_markup()


def create_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Сохранить", callback_data="create_confirm:save")
    builder.button(text="Отменить", callback_data="create_confirm:cancel")
    builder.adjust(2)
    return builder.as_markup()


def events_list_keyboard(items: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for event_id, title in items:
        builder.button(text=title, callback_data=f"event_view:{event_id}")
    builder.adjust(1)
    return builder.as_markup()


def event_actions_keyboard(event_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Изменить", callback_data=f"event_edit:{event_id}")
    builder.button(text="Удалить", callback_data=f"event_delete_ask:{event_id}")
    builder.button(text="К списку мероприятий", callback_data="events_list")
    builder.adjust(2, 1)
    return builder.as_markup()


def delete_confirm_keyboard(event_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Да, удалить", callback_data=f"event_delete_confirm:{event_id}")
    builder.button(text="Нет", callback_data=f"event_cancel_delete:{event_id}")
    builder.adjust(2)
    return builder.as_markup()


def edit_fields_keyboard(event_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Изменить название", callback_data=f"edit_title:{event_id}")
    builder.button(text="Изменить дату", callback_data=f"edit_date:{event_id}")
    builder.button(text="Изменить повторение", callback_data=f"edit_repeat:{event_id}")
    builder.button(text="Изменить дни до напоминания", callback_data=f"edit_days:{event_id}")
    builder.button(text="Изменить напоминания в день", callback_data=f"edit_times:{event_id}")
    builder.button(text="Назад к событию", callback_data=f"edit_back_event:{event_id}")
    builder.adjust(1)
    return builder.as_markup()
