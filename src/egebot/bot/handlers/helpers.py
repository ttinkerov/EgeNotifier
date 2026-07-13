from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message

from egebot.bot.keyboards import (
    captcha_again,
    guest_keyboard,
    member_keyboard,
    refresh_scores as refresh_scores_kb,
)
from egebot.bot.states import AuthFlow
from egebot.content import ui_copy as t
from egebot.domain.exam_snapshot import FetchScoresStatus
from egebot.domain.models import SignInStatus
from egebot.services.auth import AuthService
from egebot.services.scores import SCORES_PARSE_MODE, ScoresService
from egebot.services.session import SessionService
from loguru import logger


async def start_auth_flow(message: Message, state: FSMContext, session_svc: SessionService) -> None:
    user = message.from_user
    if user is None:
        return
    await session_svc.begin_auth(user.id, state)
    await state.set_state(AuthFlow.name)
    await message.answer(t.ASK_FULL_NAME, reply_markup=guest_keyboard())


async def end_session(message: Message, state: FSMContext, session_svc: SessionService) -> None:
    user = message.from_user
    if user is None:
        return
    had_session = await session_svc.is_logged_in(user.id)
    await session_svc.clear(user.id, state)
    text = t.EXIT_OK if had_session else t.EXIT_EMPTY
    if had_session:
        logger.info("Session cleared for user {}", user.id)
    await message.answer(text, reply_markup=guest_keyboard())


async def send_region_hint(message: Message, subject_code: int) -> None:
    hint = t.REGION_HINTS.get(subject_code)
    if hint:
        await message.answer(hint)


async def send_captcha(message: Message, auth_svc: AuthService, telegram_id: int) -> bool:
    captcha = await auth_svc.request_captcha(telegram_id)
    if captcha is None:
        await message.answer(t.CAPTCHA_DOWN, reply_markup=captcha_again())
        return False
    await message.answer_photo(
        BufferedInputFile(captcha.image, filename="captcha.jpg"),
        caption=t.ASK_CAPTCHA,
        reply_markup=captcha_again(),
    )
    return True


async def send_scores(message: Message, session_svc: SessionService, scores_svc: ScoresService) -> None:
    user = message.from_user
    if user is None:
        return

    account = await session_svc.get_account(user.id)
    if account is None:
        await message.answer(t.NEED_AUTH, reply_markup=guest_keyboard())
        return

    result = await scores_svc.fetch_for_account(account)
    if result.status is FetchScoresStatus.PORTAL_DOWN:
        await message.answer(t.PORTAL_DOWN, reply_markup=member_keyboard())
        return
    if result.status is FetchScoresStatus.EMPTY:
        await message.answer(t.NO_SCORES_YET, reply_markup=refresh_scores_kb())
        return
    if result.status is FetchScoresStatus.UNAUTHORIZED:
        await session_svc.clear(user.id)
        await message.answer(t.SESSION_EXPIRED, reply_markup=guest_keyboard())
        return
    if result.status is not FetchScoresStatus.OK:
        await message.answer(t.NEED_AUTH, reply_markup=guest_keyboard())
        return

    text = await scores_svc.render(user.id, result.exams, account=account)
    await message.answer(text, parse_mode=SCORES_PARSE_MODE, reply_markup=refresh_scores_kb())


async def send_history(message: Message, session_svc: SessionService, scores_svc: ScoresService) -> None:
    user = message.from_user
    if user is None:
        return

    account = await session_svc.get_account(user.id)
    if account is None:
        await message.answer(t.NEED_AUTH_HISTORY, reply_markup=guest_keyboard())
        return

    text = await scores_svc.render_history(user.id)
    await message.answer(text, parse_mode=SCORES_PARSE_MODE, reply_markup=refresh_scores_kb())


async def finish_login(
    message: Message,
    state: FSMContext,
    auth_svc: AuthService,
    session_svc: SessionService,
    scores_svc: ScoresService,
) -> SignInStatus:
    user = message.from_user
    if user is None:
        return SignInStatus.BAD_CREDENTIALS

    await message.answer(t.AUTH_PENDING)
    status, exams = await auth_svc.complete_login(user.id)

    if status is SignInStatus.OK:
        await state.clear()
        await message.answer(t.AUTH_OK, reply_markup=member_keyboard())
        logger.info("User {} signed in", user.id)
        account = await session_svc.get_account(user.id)
        if account:
            await send_region_hint(message, account.subject_code)
        if exams:
            text = await scores_svc.render(user.id, exams, account=account)
            await message.answer(text, parse_mode=SCORES_PARSE_MODE, reply_markup=refresh_scores_kb())
        else:
            await send_scores(message, session_svc, scores_svc)
        return status

    await auth_svc.reset_captcha_step(user.id)
    await state.set_state(AuthFlow.captcha)
    if status is SignInStatus.BAD_CREDENTIALS:
        await message.answer(t.CAPTCHA_RETRY, reply_markup=captcha_again())
    else:
        await message.answer(t.PORTAL_DOWN, reply_markup=captcha_again())
    await send_captcha(message, auth_svc, user.id)
    return status


async def recover_captcha_step(
    message: Message,
    auth_svc: AuthService,
    telegram_id: int,
) -> None:
    await auth_svc.reset_captcha_step(telegram_id)
    await message.answer(t.CAPTCHA_RETRY)
    await send_captcha(message, auth_svc, telegram_id)
