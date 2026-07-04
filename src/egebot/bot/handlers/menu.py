from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from egebot.bot.handlers.helpers import end_session, send_scores, start_auth_flow
from egebot.bot.handlers.settings import show_settings
from egebot.bot.keyboards import (
    KEY_CALENDAR,
    KEY_EXIT,
    KEY_FAQ,
    KEY_SCORES,
    KEY_SETTINGS,
    KEY_SIGN_IN,
    guest_keyboard,
    member_keyboard,
)
from egebot.content import ui_copy as t
from egebot.services.scores import ScoresService
from egebot.services.session import SessionService
from egebot.services.settings import SettingsService

router = Router(name="menu")


@router.message(F.text == KEY_FAQ)
async def tap_faq(message: Message) -> None:
    await message.answer(t.FAQ)


@router.message(F.text == KEY_CALENDAR)
async def tap_calendar(message: Message) -> None:
    await message.answer(t.RELEASE_CALENDAR)


@router.message(F.text == KEY_SIGN_IN)
async def tap_sign_in(message: Message, state: FSMContext, session_svc: SessionService) -> None:
    user = message.from_user
    if user is None:
        return
    if await session_svc.is_logged_in(user.id):
        await message.answer(t.SESSION_ACTIVE, reply_markup=member_keyboard())
        return
    await start_auth_flow(message, state, session_svc)


@router.message(F.text == KEY_SCORES)
async def tap_scores(
    message: Message,
    session_svc: SessionService,
    scores_svc: ScoresService,
) -> None:
    await send_scores(message, session_svc, scores_svc)


@router.message(F.text == KEY_SETTINGS)
async def tap_settings(message: Message, settings_svc: SettingsService) -> None:
    await show_settings(message, settings_svc)


@router.message(F.text == KEY_EXIT)
async def tap_exit(message: Message, state: FSMContext, session_svc: SessionService) -> None:
    await end_session(message, state, session_svc)
