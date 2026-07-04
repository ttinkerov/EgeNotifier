from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from egebot.bot.handlers.helpers import (
    finish_login,
    send_captcha,
    send_region_hint,
)
from egebot.bot.keyboards import captcha_again, subjects_toggle
from egebot.bot.states import AuthFlow
from egebot.content import ui_copy as t
from egebot.services.auth import AuthService
from egebot.services.scores import ScoresService
from egebot.services.session import SessionService

router = Router(name="auth")


@router.message(AuthFlow.name)
async def on_name(message: Message, state: FSMContext, auth_svc: AuthService) -> None:
    user = message.from_user
    if user is None or not message.text:
        await message.answer(t.BAD_FULL_NAME)
        return
    if not await auth_svc.save_name(user.id, message.text.strip()):
        await message.answer(t.BAD_FULL_NAME)
        return
    await state.set_state(AuthFlow.region)
    await message.answer(t.ASK_SUBJECT_CODE, reply_markup=subjects_toggle())


@router.message(AuthFlow.region)
async def on_region(message: Message, state: FSMContext, auth_svc: AuthService) -> None:
    user = message.from_user
    if user is None or not message.text:
        await message.answer(t.BAD_SUBJECT_CODE, reply_markup=subjects_toggle())
        return
    ok, description = await auth_svc.save_region(user.id, message.text.strip())
    if not ok or description is None:
        await message.answer(t.BAD_SUBJECT_CODE, reply_markup=subjects_toggle())
        return
    await state.set_state(AuthFlow.document)
    await message.answer(description)
    await send_region_hint(message, int(message.text.strip()))
    await message.answer(t.ASK_DOCUMENT)


@router.message(AuthFlow.document)
async def on_document(message: Message, state: FSMContext, auth_svc: AuthService) -> None:
    user = message.from_user
    if user is None or not message.text:
        await message.answer(t.BAD_DOCUMENT)
        return
    if not await auth_svc.save_document(user.id, message.text.strip()):
        await message.answer(t.BAD_DOCUMENT)
        return
    await state.set_state(AuthFlow.captcha)
    await send_captcha(message, auth_svc, user.id)


@router.message(AuthFlow.captcha, F.text.len() == 6, F.text.regexp(r"^\d{6}$"))
async def on_captcha(
    message: Message,
    state: FSMContext,
    auth_svc: AuthService,
    session_svc: SessionService,
    scores_svc: ScoresService,
) -> None:
    user = message.from_user
    if user is None or message.text is None:
        return
    if not await auth_svc.save_captcha_answer(user.id, message.text):
        await message.answer(t.BAD_CAPTCHA, reply_markup=captcha_again())
        return
    await finish_login(message, state, auth_svc, session_svc, scores_svc)


@router.message(AuthFlow.captcha)
async def on_captcha_invalid(message: Message) -> None:
    await message.answer(t.BAD_CAPTCHA, reply_markup=captcha_again())
