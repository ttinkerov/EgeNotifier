from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger

from egebot.bot.handlers.helpers import (
    recover_captcha_step,
    send_scores,
    start_auth_flow,
)
from egebot.bot.keyboards import guest_keyboard, refresh_scores as refresh_scores_kb, subjects_toggle
from egebot.bot.states import AuthFlow
from egebot.content import ui_copy as t
from egebot.content.federal_subjects import render_subject_picker
from egebot.domain.exam_snapshot import FetchScoresStatus
from egebot.services.auth import AuthService
from egebot.services.scores import SCORES_PARSE_MODE, ScoresService
from egebot.services.session import SessionService

router = Router(name="callbacks")


@router.callback_query(F.data == "geo:expand")
async def expand_regions(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    try:
        await callback.message.edit_text(
            render_subject_picker(),
            reply_markup=subjects_toggle(collapsed=False),
        )
    except TelegramBadRequest as exc:
        log.debug("Region expand edit skipped: {}", exc)
    await callback.answer()


@router.callback_query(F.data == "geo:collapse")
async def collapse_regions(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    try:
        await callback.message.edit_text(
            t.ASK_SUBJECT_CODE,
            reply_markup=subjects_toggle(collapsed=True),
        )
    except TelegramBadRequest as exc:
        log.debug("Region collapse edit skipped: {}", exc)
    await callback.answer()


@router.callback_query(F.data == "captcha:new")
async def new_captcha(
    callback: CallbackQuery,
    state: FSMContext,
    auth_svc: AuthService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return
    await state.set_state(AuthFlow.captcha)
    await recover_captcha_step(callback.message, auth_svc, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "scores:refresh")
async def on_scores_refresh(
    callback: CallbackQuery,
    session_svc: SessionService,
    scores_svc: ScoresService,
) -> None:
    if callback.message is None or callback.from_user is None:
        await callback.answer()
        return
    if not await session_svc.is_logged_in(callback.from_user.id):
        await callback.answer(t.NEED_AUTH, show_alert=True)
        return

    result = await scores_svc.fetch_for_user(callback.from_user.id)
    if result.status is FetchScoresStatus.PORTAL_DOWN:
        await callback.answer(t.PORTAL_DOWN, show_alert=True)
        return
    if result.status is FetchScoresStatus.EMPTY:
        await callback.answer("Пока пусто")
        return
    if result.status is not FetchScoresStatus.OK:
        await callback.answer(t.NEED_AUTH, show_alert=True)
        return

    text = await scores_svc.render(callback.from_user.id, result.exams)
    try:
        await callback.message.edit_text(
            text,
            parse_mode=SCORES_PARSE_MODE,
            reply_markup=refresh_scores_kb(),
        )
        await callback.answer("Обновлено")
    except TelegramBadRequest:
        await callback.answer(t.SCORES_FRESH)


@router.callback_query(F.data == "auth:retry")
async def on_auth_retry(
    callback: CallbackQuery,
    state: FSMContext,
    auth_svc: AuthService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return
    await state.set_state(AuthFlow.captcha)
    await recover_captcha_step(callback.message, auth_svc, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "auth:reset")
async def on_auth_reset(
    callback: CallbackQuery,
    state: FSMContext,
    session_svc: SessionService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return
    await start_auth_flow(callback.message, state, session_svc)
    await callback.answer()
