from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from egebot.bot.keyboards import (
    KEY_UNIVERSITIES,
    guest_keyboard,
    uni_fields,
    uni_funding,
    uni_regions,
    uni_restart,
)
from egebot.content import uni_copy as t
from egebot.content.university_catalog import scores_from_exams
from egebot.domain.exam_snapshot import FetchScoresStatus
from egebot.domain.models import TgAccount
from egebot.domain.universities import FundingType, StudyField, UserScores
from egebot.services.scores import ScoresService
from egebot.services.session import SessionService
from egebot.services.universities import UniversitiesService

router = Router(name="universities")


async def _load_portal_scores(
    account: TgAccount,
    scores_svc: ScoresService,
) -> UserScores | None:
    result = await scores_svc.fetch_for_account(account)
    if result.status is not FetchScoresStatus.OK:
        return None
    scores = scores_from_exams(result.exams)
    return scores if scores.subjects else None


async def start_university_flow(
    message: Message,
    state: FSMContext,
    session_svc: SessionService,
    scores_svc: ScoresService,
) -> None:
    user = message.from_user
    if user is None:
        return

    await state.clear()
    await message.answer(t.UNI_INTRO)

    account = await session_svc.get_account(user.id)
    if account is None:
        await message.answer(t.UNI_NEED_AUTH, reply_markup=guest_keyboard())
        return

    scores = await _load_portal_scores(account, scores_svc)
    if scores is None:
        await message.answer(t.UNI_SCORES_EMPTY, reply_markup=guest_keyboard())
        return

    await state.update_data(uni_scores=scores.subjects)
    await message.answer(
        f"*Баллы с портала (все сданные предметы):*\n{t.format_user_scores(scores)}\n\n"
        "_Подбор идёт только по этим результатам._"
    )
    await _ask_funding(message)


async def _ask_funding(message: Message) -> None:
    await message.answer(t.UNI_ASK_FUNDING, reply_markup=uni_funding())


async def _ask_region(message: Message) -> None:
    await message.answer(t.UNI_ASK_REGION, reply_markup=uni_regions())


async def _ask_field(message: Message) -> None:
    await message.answer(t.UNI_ASK_FIELD, reply_markup=uni_fields())


async def _show_results(
    message: Message,
    state: FSMContext,
    uni_svc: UniversitiesService,
    scores_svc: ScoresService,
    session_svc: SessionService,
) -> None:
    user = message.from_user
    if user is None:
        return

    data = await state.get_data()
    raw_scores = data.get("uni_scores")
    if not raw_scores:
        account = await session_svc.get_account(user.id)
        if account is not None:
            scores = await _load_portal_scores(account, scores_svc)
            if scores is not None:
                raw_scores = scores.subjects
                await state.update_data(uni_scores=raw_scores)

    if not raw_scores:
        await message.answer(t.UNI_SCORES_EMPTY)
        return

    scores = UserScores(subjects=raw_scores)
    funding_raw = data.get("uni_funding")
    funding = None
    if funding_raw not in (None, "any"):
        try:
            funding = FundingType(funding_raw)
        except ValueError:
            await message.answer(t.UNI_ASK_FUNDING, reply_markup=uni_funding())
            return

    region_raw = data.get("uni_region")
    region_code = None
    if region_raw not in (None, "any", 0, "0"):
        try:
            region_code = int(region_raw)
        except (TypeError, ValueError):
            await message.answer(t.UNI_ASK_REGION, reply_markup=uni_regions())
            return

    field_raw = data.get("uni_field")
    if not field_raw:
        await message.answer(t.UNI_ASK_FIELD, reply_markup=uni_fields())
        return

    try:
        field = StudyField(field_raw)
    except ValueError:
        await message.answer(t.UNI_ASK_FIELD, reply_markup=uni_fields())
        return

    results = uni_svc.find_best(
        scores,
        funding=funding,
        region_code=region_code,
        field=field,
    )
    pages = t.format_match_pages(results)
    for index, page in enumerate(pages):
        markup = uni_restart() if index == len(pages) - 1 else None
        await message.answer(page, reply_markup=markup)
    await state.clear()


@router.message(Command("universities", "vuz", "uni"))
async def cmd_universities(
    message: Message,
    state: FSMContext,
    session_svc: SessionService,
    scores_svc: ScoresService,
) -> None:
    await start_university_flow(message, state, session_svc, scores_svc)


@router.message(F.text == KEY_UNIVERSITIES)
async def tap_universities(
    message: Message,
    state: FSMContext,
    session_svc: SessionService,
    scores_svc: ScoresService,
) -> None:
    await start_university_flow(message, state, session_svc, scores_svc)


@router.callback_query(F.data.startswith("uni:funding:"))
async def on_funding(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None or callback.data is None:
        await callback.answer()
        return
    funding = callback.data.removeprefix("uni:funding:")
    await state.update_data(uni_funding=funding)
    await _ask_region(callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith("uni:region:"))
async def on_region(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None or callback.data is None:
        await callback.answer()
        return
    region = callback.data.removeprefix("uni:region:")
    await state.update_data(uni_region=region)
    await _ask_field(callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith("uni:field:"))
async def on_field(
    callback: CallbackQuery,
    state: FSMContext,
    uni_svc: UniversitiesService,
    scores_svc: ScoresService,
    session_svc: SessionService,
) -> None:
    if callback.message is None or callback.data is None:
        await callback.answer()
        return
    field = callback.data.removeprefix("uni:field:")
    await state.update_data(uni_field=field)
    await _show_results(callback.message, state, uni_svc, scores_svc, session_svc)
    await callback.answer()


@router.callback_query(F.data == "uni:restart")
async def on_restart(
    callback: CallbackQuery,
    state: FSMContext,
    session_svc: SessionService,
    scores_svc: ScoresService,
) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await start_university_flow(callback.message, state, session_svc, scores_svc)
    await callback.answer()
