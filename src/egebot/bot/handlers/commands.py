from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from egebot.bot.handlers.helpers import end_session, send_scores, start_auth_flow
from egebot.bot.keyboards import guest_keyboard, member_keyboard
from egebot.config import Settings
from egebot.content import ui_copy as t
from egebot.services.scores import ScoresService
from egebot.services.session import SessionService

router = Router(name="commands")


@router.message(CommandStart())
async def on_start(message: Message, state: FSMContext, session_svc: SessionService) -> None:
    user = message.from_user
    if user is None:
        return
    if await session_svc.is_logged_in(user.id):
        await message.answer(t.SESSION_ACTIVE, reply_markup=member_keyboard())
        return
    await message.answer(t.WELCOME, reply_markup=guest_keyboard())
    await start_auth_flow(message, state, session_svc)


@router.message(Command("exit", "logout", "stop"))
async def on_exit(message: Message, state: FSMContext, session_svc: SessionService) -> None:
    await end_session(message, state, session_svc)


@router.message(Command("scores", "check"))
async def on_scores(
    message: Message,
    session_svc: SessionService,
    scores_svc: ScoresService,
) -> None:
    await send_scores(message, session_svc, scores_svc)


@router.message(Command("help"))
async def on_help(message: Message) -> None:
    await message.answer(t.FAQ)


@router.message(Command("version"))
async def on_version(message: Message, settings: Settings) -> None:
    if message.from_user and message.from_user.id in settings.admin_ids:
        await message.answer(f"EgeNotifier {settings.app_version}")
