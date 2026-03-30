from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.constants import MAIN_MENU_ADD, MAIN_MENU_HELP, MAIN_MENU_LIST


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MAIN_MENU_ADD), KeyboardButton(text=MAIN_MENU_LIST)],
            [KeyboardButton(text=MAIN_MENU_HELP)],
        ],
        resize_keyboard=True,
    )
