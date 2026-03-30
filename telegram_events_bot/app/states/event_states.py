from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class CreateEventState(StatesGroup):
    waiting_title = State()
    waiting_date = State()
    waiting_repeat_type = State()
    waiting_remind_before_days = State()
    waiting_reminders_per_day = State()
    waiting_confirm = State()


class EditEventState(StatesGroup):
    waiting_title = State()
    waiting_date = State()
