from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from egebot.bot.keyboards import settings_keyboard
from egebot.content import ui_copy as t
from egebot.services.settings import SettingsService

router = Router(name="settings")


async def show_settings(message: Message, settings_svc: SettingsService) -> None:
    user = message.from_user
    if user is None:
        return
    panel = await settings_svc.get_panel(user.id)
    if panel is None:
        await message.answer(t.SETTINGS_NEED_AUTH)
        return
    text, spoiler_enabled = panel
    await message.answer(text, reply_markup=settings_keyboard(spoiler_enabled))


async def _edit_settings_message(
    message: Message,
    text: str,
    spoiler_enabled: bool,
) -> None:
    markup = settings_keyboard(spoiler_enabled)
    try:
        await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        try:
            await message.edit_reply_markup(reply_markup=markup)
        except TelegramBadRequest:
            await message.answer(text, reply_markup=markup)


@router.message(Command("settings"))
async def cmd_settings(message: Message, settings_svc: SettingsService) -> None:
    await show_settings(message, settings_svc)


@router.callback_query(F.data == "settings:spoiler:toggle")
async def toggle_spoiler(callback: CallbackQuery, settings_svc: SettingsService) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return
    result = await settings_svc.toggle_spoiler(callback.from_user.id)
    if result is None:
        await callback.answer(t.SETTINGS_NEED_AUTH, show_alert=True)
        return
    enabled, text = result
    await _edit_settings_message(callback.message, text, enabled)
    await callback.answer(t.SETTINGS_SPOILER_TOGGLED)
