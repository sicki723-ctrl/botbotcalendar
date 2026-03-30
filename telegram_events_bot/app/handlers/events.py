from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.constants import (
    MAIN_MENU_ADD,
    MAIN_MENU_LIST,
    MAX_TITLE_LENGTH,
    REPEAT_RU_LABELS,
)
from app.database.models import RepeatType
from app.keyboards.inline import (
    create_confirm_keyboard,
    delete_confirm_keyboard,
    edit_fields_keyboard,
    event_actions_keyboard,
    events_list_keyboard,
    remind_before_days_keyboard,
    reminders_per_day_keyboard,
    repeat_type_keyboard,
)
from app.keyboards.reply import main_menu_keyboard
from app.services.event_service import EventService
from app.states.event_states import CreateEventState, EditEventState
from app.utils.date_utils import parse_user_date
from app.utils.formatters import build_event_details_text, build_event_draft_text


logger = logging.getLogger(__name__)


def _parse_callback_parts(data: str, expected_prefix: str, expected_len: int) -> list[str] | None:
    parts = data.split(":")
    if len(parts) != expected_len:
        return None
    if parts[0] != expected_prefix:
        return None
    return parts


def get_events_router(event_service: EventService) -> Router:
    router = Router(name="events")

    @router.message(F.text == MAIN_MENU_ADD)
    async def add_event_start(message: Message, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(CreateEventState.waiting_title)
        await message.answer(
            "Введите название мероприятия (до 120 символов):",
            reply_markup=main_menu_keyboard(),
        )

    @router.message(StateFilter(CreateEventState.waiting_title))
    async def create_event_title(message: Message, state: FSMContext) -> None:
        title = (message.text or "").strip()
        if not title:
            await message.answer("Название не может быть пустым. Введите название:")
            return
        if len(title) > MAX_TITLE_LENGTH:
            await message.answer(f"Название слишком длинное. Максимум {MAX_TITLE_LENGTH} символов.")
            return

        await state.update_data(title=title)
        await state.set_state(CreateEventState.waiting_date)
        await message.answer("Введите дату события в формате ДД.ММ.ГГГГ:")

    @router.message(StateFilter(CreateEventState.waiting_date))
    async def create_event_date(message: Message, state: FSMContext) -> None:
        raw_date = (message.text or "").strip()
        try:
            event_date = parse_user_date(raw_date)
        except ValueError:
            await message.answer("Неверный формат даты. Пример: 20.07.2026")
            return

        today = datetime.now(ZoneInfo(event_service.timezone_name)).date()
        if event_date < today:
            await message.answer("Дата не может быть в прошлом. Введите будущую дату:")
            return

        await state.update_data(event_date=event_date.isoformat())
        await state.set_state(CreateEventState.waiting_repeat_type)
        await message.answer(
            "Выберите тип повторения:",
            reply_markup=repeat_type_keyboard(prefix="create_repeat"),
        )

    @router.callback_query(StateFilter(CreateEventState.waiting_repeat_type), F.data.startswith("create_repeat:"))
    async def create_event_repeat(callback: CallbackQuery, state: FSMContext) -> None:
        parts = _parse_callback_parts(callback.data, "create_repeat", 2)
        if parts is None:
            await callback.answer("Некорректный выбор", show_alert=True)
            return

        repeat_raw = parts[1]
        try:
            repeat_type = RepeatType(repeat_raw)
        except ValueError:
            await callback.answer("Некорректный тип повторения", show_alert=True)
            return

        await state.update_data(repeat_type=repeat_type.value)
        await state.set_state(CreateEventState.waiting_remind_before_days)
        await callback.message.edit_text(
            "За сколько дней до события начинать напоминания?",
            reply_markup=remind_before_days_keyboard(prefix="create_days"),
        )
        await callback.answer()

    @router.callback_query(
        StateFilter(CreateEventState.waiting_remind_before_days),
        F.data.startswith("create_days:"),
    )
    async def create_event_remind_before_days(callback: CallbackQuery, state: FSMContext) -> None:
        parts = _parse_callback_parts(callback.data, "create_days", 2)
        if parts is None:
            await callback.answer("Некорректный выбор", show_alert=True)
            return

        try:
            remind_before_days = int(parts[1])
        except ValueError:
            await callback.answer("Некорректное число", show_alert=True)
            return

        await state.update_data(remind_before_days=remind_before_days)
        await state.set_state(CreateEventState.waiting_reminders_per_day)

        await callback.message.edit_text(
            "Сколько раз в день отправлять напоминания?",
            reply_markup=reminders_per_day_keyboard(prefix="create_times"),
        )
        await callback.answer()

    @router.callback_query(
        StateFilter(CreateEventState.waiting_reminders_per_day),
        F.data.startswith("create_times:"),
    )
    async def create_event_reminders_per_day(callback: CallbackQuery, state: FSMContext) -> None:
        parts = _parse_callback_parts(callback.data, "create_times", 2)
        if parts is None:
            await callback.answer("Некорректный выбор", show_alert=True)
            return

        try:
            reminders_per_day = int(parts[1])
        except ValueError:
            await callback.answer("Некорректное число", show_alert=True)
            return

        if reminders_per_day not in {1, 2, 3}:
            await callback.answer("Поддерживается только 1, 2 или 3", show_alert=True)
            return

        await state.update_data(reminders_per_day=reminders_per_day)
        await state.set_state(CreateEventState.waiting_confirm)

        data = await state.get_data()
        text = build_event_draft_text(data, REPEAT_RU_LABELS)
        await callback.message.edit_text(text, reply_markup=create_confirm_keyboard())
        await callback.answer()

    @router.callback_query(StateFilter(CreateEventState.waiting_confirm), F.data.startswith("create_confirm:"))
    async def create_event_confirm(callback: CallbackQuery, state: FSMContext) -> None:
        parts = _parse_callback_parts(callback.data, "create_confirm", 2)
        if parts is None:
            await callback.answer("Некорректное действие", show_alert=True)
            return

        action = parts[1]
        if action == "cancel":
            await state.clear()
            await callback.message.edit_text("Создание мероприятия отменено.")
            await callback.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
            await callback.answer()
            return

        if action != "save":
            await callback.answer("Некорректное действие", show_alert=True)
            return

        data = await state.get_data()
        try:
            await event_service.create_event(
                telegram_id=callback.from_user.id,
                title=data["title"],
                event_date_iso=data["event_date"],
                repeat_type=RepeatType(data["repeat_type"]),
                remind_before_days=int(data["remind_before_days"]),
                reminders_per_day=int(data["reminders_per_day"]),
            )
        except Exception:
            logger.exception("Ошибка при создании события telegram_id=%s", callback.from_user.id)
            await callback.message.answer("Не удалось сохранить мероприятие. Попробуйте позже.")
            await callback.answer()
            return

        await state.clear()
        await callback.message.edit_text("Мероприятие успешно сохранено.")
        await callback.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
        await callback.answer()

    @router.message(F.text == MAIN_MENU_LIST)
    async def show_my_events(message: Message) -> None:
        try:
            items = await event_service.list_events_for_user(message.from_user.id)
        except Exception:
            logger.exception("Ошибка чтения списка событий telegram_id=%s", message.from_user.id)
            await message.answer("Не удалось загрузить список мероприятий. Попробуйте позже.")
            return

        if not items:
            await message.answer("У вас пока нет мероприятий. Нажмите «Добавить мероприятие».")
            return

        keyboard_items = [
            (event.id, f"{event.title} — {next_date.strftime('%d.%m.%Y')}")
            for event, next_date in items
        ]
        await message.answer("Ваши мероприятия:", reply_markup=events_list_keyboard(keyboard_items))

    @router.callback_query(F.data == "events_list")
    async def show_my_events_callback(callback: CallbackQuery) -> None:
        try:
            items = await event_service.list_events_for_user(callback.from_user.id)
        except Exception:
            logger.exception("Ошибка чтения списка событий telegram_id=%s", callback.from_user.id)
            await callback.answer("Ошибка загрузки", show_alert=True)
            return

        if not items:
            await callback.message.edit_text("У вас пока нет мероприятий.")
            await callback.answer()
            return

        keyboard_items = [
            (event.id, f"{event.title} — {next_date.strftime('%d.%m.%Y')}")
            for event, next_date in items
        ]
        await callback.message.edit_text("Ваши мероприятия:", reply_markup=events_list_keyboard(keyboard_items))
        await callback.answer()

    @router.callback_query(F.data.startswith("event_view:"))
    async def event_view(callback: CallbackQuery) -> None:
        parts = _parse_callback_parts(callback.data, "event_view", 2)
        if parts is None:
            await callback.answer("Некорректное действие", show_alert=True)
            return

        event_id = int(parts[1])
        item = await event_service.get_event_for_user(callback.from_user.id, event_id)
        if item is None:
            await callback.answer("Событие уже удалено или недоступно", show_alert=True)
            return

        event, next_date = item
        text = build_event_details_text(event, next_date, REPEAT_RU_LABELS)
        await callback.message.edit_text(text, reply_markup=event_actions_keyboard(event.id))
        await callback.answer()

    @router.callback_query(F.data.startswith("event_delete_ask:"))
    async def event_delete_ask(callback: CallbackQuery) -> None:
        parts = _parse_callback_parts(callback.data, "event_delete_ask", 2)
        if parts is None:
            await callback.answer("Некорректное действие", show_alert=True)
            return

        event_id = int(parts[1])
        item = await event_service.get_event_for_user(callback.from_user.id, event_id)
        if item is None:
            await callback.answer("Событие уже удалено или недоступно", show_alert=True)
            return

        await callback.message.edit_text(
            "Подтвердите удаление мероприятия:",
            reply_markup=delete_confirm_keyboard(event_id),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("event_delete_confirm:"))
    async def event_delete_confirm(callback: CallbackQuery) -> None:
        parts = _parse_callback_parts(callback.data, "event_delete_confirm", 2)
        if parts is None:
            await callback.answer("Некорректное действие", show_alert=True)
            return

        event_id = int(parts[1])
        result = await event_service.delete_event(callback.from_user.id, event_id)
        if not result:
            await callback.answer("Событие уже удалено или недоступно", show_alert=True)
            return

        await callback.message.edit_text("Мероприятие удалено.")
        await callback.answer()

    @router.callback_query(F.data.startswith("event_edit:"))
    async def event_edit_menu(callback: CallbackQuery, state: FSMContext) -> None:
        parts = _parse_callback_parts(callback.data, "event_edit", 2)
        if parts is None:
            await callback.answer("Некорректное действие", show_alert=True)
            return

        event_id = int(parts[1])
        item = await event_service.get_event_for_user(callback.from_user.id, event_id)
        if item is None:
            await callback.answer("Событие уже удалено или недоступно", show_alert=True)
            return

        await state.clear()
        await callback.message.edit_text(
            "Что хотите изменить?",
            reply_markup=edit_fields_keyboard(event_id),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("edit_title:"))
    async def edit_title_start(callback: CallbackQuery, state: FSMContext) -> None:
        event_id = int(_parse_callback_parts(callback.data, "edit_title", 2)[1])
        item = await event_service.get_event_for_user(callback.from_user.id, event_id)
        if item is None:
            await callback.answer("Событие уже удалено или недоступно", show_alert=True)
            return

        await state.clear()
        await state.update_data(edit_event_id=event_id)
        await state.set_state(EditEventState.waiting_title)
        await callback.message.answer("Введите новое название:")
        await callback.answer()

    @router.message(StateFilter(EditEventState.waiting_title))
    async def edit_title_finish(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        event_id = data.get("edit_event_id")
        if not event_id:
            await state.clear()
            await message.answer("Сессия редактирования завершена. Повторите действие.")
            return

        title = (message.text or "").strip()
        if not title:
            await message.answer("Название не может быть пустым. Введите название:")
            return
        if len(title) > MAX_TITLE_LENGTH:
            await message.answer(f"Название слишком длинное. Максимум {MAX_TITLE_LENGTH} символов.")
            return

        await event_service.update_event_field(message.from_user.id, int(event_id), "title", title)
        await state.clear()
        item = await event_service.get_event_for_user(message.from_user.id, int(event_id))
        if item is None:
            await message.answer("Событие больше недоступно.")
            return
        event, next_date = item
        await message.answer(
            "Название обновлено.\n\n" + build_event_details_text(event, next_date, REPEAT_RU_LABELS),
            reply_markup=event_actions_keyboard(event.id),
        )

    @router.callback_query(F.data.startswith("edit_date:"))
    async def edit_date_start(callback: CallbackQuery, state: FSMContext) -> None:
        event_id = int(_parse_callback_parts(callback.data, "edit_date", 2)[1])
        item = await event_service.get_event_for_user(callback.from_user.id, event_id)
        if item is None:
            await callback.answer("Событие уже удалено или недоступно", show_alert=True)
            return

        await state.clear()
        await state.update_data(edit_event_id=event_id)
        await state.set_state(EditEventState.waiting_date)
        await callback.message.answer("Введите новую дату в формате ДД.ММ.ГГГГ:")
        await callback.answer()

    @router.message(StateFilter(EditEventState.waiting_date))
    async def edit_date_finish(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        event_id = data.get("edit_event_id")
        if not event_id:
            await state.clear()
            await message.answer("Сессия редактирования завершена. Повторите действие.")
            return

        event_date = parse_user_date((message.text or "").strip())
        today = datetime.now(ZoneInfo(event_service.timezone_name)).date()
        if event_date < today:
            await message.answer("Дата не может быть в прошлом. Введите будущую дату:")
            return

        await event_service.update_event_field(message.from_user.id, int(event_id), "event_date", event_date.isoformat())
        await state.clear()
        item = await event_service.get_event_for_user(message.from_user.id, int(event_id))
        if item is None:
            await message.answer("Событие больше недоступно.")
            return
        event, next_date = item
        await message.answer(
            "Дата обновлена.\n\n" + build_event_details_text(event, next_date, REPEAT_RU_LABELS),
            reply_markup=event_actions_keyboard(event.id),
        )

    @router.callback_query(F.data.startswith("edit_repeat:"))
    async def edit_repeat_select(callback: CallbackQuery) -> None:
        event_id = int(_parse_callback_parts(callback.data, "edit_repeat", 2)[1])
        await callback.message.edit_text(
            "Выберите новый тип повторения:",
            reply_markup=repeat_type_keyboard(prefix=f"edit_set_repeat:{event_id}"),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("edit_set_repeat:"))
    async def edit_repeat_set(callback: CallbackQuery) -> None:
        parts = callback.data.split(":")
        event_id = int(parts[1])
        repeat_type = RepeatType(parts[3])
        await event_service.update_event_field(callback.from_user.id, event_id, "repeat_type", repeat_type.value)
        item = await event_service.get_event_for_user(callback.from_user.id, event_id)
        if item is None:
            await callback.answer("Событие уже удалено или недоступно", show_alert=True)
            return
        event, next_date = item
        await callback.message.edit_text(
            "Тип повторения обновлен.\n\n" + build_event_details_text(event, next_date, REPEAT_RU_LABELS),
            reply_markup=event_actions_keyboard(event.id),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("edit_days:"))
    async def edit_days_select(callback: CallbackQuery) -> None:
        event_id = int(_parse_callback_parts(callback.data, "edit_days", 2)[1])
        await callback.message.edit_text(
            "Выберите, за сколько дней начинать напоминания:",
            reply_markup=remind_before_days_keyboard(prefix=f"edit_set_days:{event_id}"),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("edit_set_days:"))
    async def edit_days_set(callback: CallbackQuery) -> None:
        parts = callback.data.split(":")
        event_id = int(parts[1])
        remind_before_days = int(parts[3])
        await event_service.update_event_field(callback.from_user.id, event_id, "remind_before_days", remind_before_days)
        item = await event_service.get_event_for_user(callback.from_user.id, event_id)
        if item is None:
            await callback.answer("Событие уже удалено или недоступно", show_alert=True)
            return
        event, next_date = item
        await callback.message.edit_text(
            "Количество дней обновлено.\n\n" + build_event_details_text(event, next_date, REPEAT_RU_LABELS),
            reply_markup=event_actions_keyboard(event.id),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("edit_times:"))
    async def edit_times_select(callback: CallbackQuery) -> None:
        event_id = int(_parse_callback_parts(callback.data, "edit_times", 2)[1])
        await callback.message.edit_text(
            "Выберите, сколько раз в день отправлять напоминание:",
            reply_markup=reminders_per_day_keyboard(prefix=f"edit_set_times:{event_id}"),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("edit_set_times:"))
    async def edit_times_set(callback: CallbackQuery) -> None:
        parts = callback.data.split(":")
        event_id = int(parts[1])
        reminders_per_day = int(parts[3])
        await event_service.update_event_field(callback.from_user.id, event_id, "reminders_per_day", reminders_per_day)
        item = await event_service.get_event_for_user(callback.from_user.id, event_id)
        if item is None:
            await callback.answer("Событие уже удалено или недоступно", show_alert=True)
            return
        event, next_date = item
        await callback.message.edit_text(
            "Количество напоминаний обновлено.\n\n" + build_event_details_text(event, next_date, REPEAT_RU_LABELS),
            reply_markup=event_actions_keyboard(event.id),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("event_cancel_delete:"))
    async def event_cancel_delete(callback: CallbackQuery) -> None:
        event_id = int(_parse_callback_parts(callback.data, "event_cancel_delete", 2)[1])
        item = await event_service.get_event_for_user(callback.from_user.id, event_id)
        if item is None:
            await callback.answer("Событие уже удалено или недоступно", show_alert=True)
            return
        event, next_date = item
        await callback.message.edit_text(
            build_event_details_text(event, next_date, REPEAT_RU_LABELS),
            reply_markup=event_actions_keyboard(event.id),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("edit_back_event:"))
    async def edit_back_event(callback: CallbackQuery) -> None:
        event_id = int(_parse_callback_parts(callback.data, "edit_back_event", 2)[1])
        item = await event_service.get_event_for_user(callback.from_user.id, event_id)
        if item is None:
            await callback.answer("Событие уже удалено или недоступно", show_alert=True)
            return
        event, next_date = item
        await callback.message.edit_text(
            build_event_details_text(event, next_date, REPEAT_RU_LABELS),
            reply_markup=event_actions_keyboard(event.id),
        )
        await callback.answer()

    return router
