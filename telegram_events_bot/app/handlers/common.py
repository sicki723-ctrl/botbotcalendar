from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.constants import MAIN_MENU_HELP
from app.keyboards.reply import main_menu_keyboard
from app.services.event_service import EventService


logger = logging.getLogger(__name__)


def get_common_router(event_service: EventService) -> Router:
    router = Router(name="common")

    @router.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        try:
            await event_service.ensure_user(message.from_user.id)
        except Exception:
            logger.exception("Ошибка при создании пользователя telegram_id=%s", message.from_user.id)
            await message.answer("Не удалось подготовить профиль. Попробуйте позже.")
            return

        await message.answer(
            "Привет! Я бот для календаря мероприятий и напоминаний.\n\n"
            "Выбирайте действие в меню ниже.",
            reply_markup=main_menu_keyboard(),
        )

    @router.message(Command("help"))
    @router.message(F.text == MAIN_MENU_HELP)
    async def cmd_help(message: Message) -> None:
        await message.answer(
            "Как пользоваться ботом:\n"
            "1) Нажмите «Добавить мероприятие».\n"
            "2) Пройдите шаги: название, дата, повторение, параметры напоминаний.\n"
            "3) В разделе «Мои мероприятия» можно посмотреть, изменить или удалить событие.\n\n"
            "Формат даты: ДД.ММ.ГГГГ (например, 20.07.2026).",
            reply_markup=main_menu_keyboard(),
        )

    return router
