from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from egebot.config import Settings
from egebot.domain.models import SignInStatus, TgAccount
from egebot.services.auth import AuthService
from egebot.services.scores import ScoresService
from egebot.services.session import SessionService
from egebot.services.watcher import ScoresWatcher
from egebot.services.admin import AdminService
from tests.fakes import (
    FakeRustest,
    InMemoryAccounts,
    InMemoryDrafts,
    InMemoryHistory,
    make_exam,
)


def _settings(**overrides: object) -> Settings:
    base = {
        "TG_API_TOKEN": "1:test",
        "DB_NAME": "egebot",
        "DB_USER": "postgres",
        "DB_PASS": "postgres",
        "poll_cooldown_sec": 0,
        "watcher_jitter_sec": 0,
        "watcher_backoff_sec": 0,
        "watcher_tick_sec": 0,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


async def _login(auth_svc: AuthService, telegram_id: int, drafts: InMemoryDrafts) -> None:
    await drafts.start(telegram_id)
    await auth_svc.save_name(telegram_id, "Иванов Иван")
    await auth_svc.save_region(telegram_id, "77")
    await auth_svc.save_document(telegram_id, "123456")
    await auth_svc.request_captcha(telegram_id)
    await auth_svc.save_captcha_answer(telegram_id, "123456")
    status, _ = await auth_svc.complete_login(telegram_id)
    assert status is SignInStatus.OK


@pytest.mark.asyncio
async def test_logout_keeps_history_and_prefs() -> None:
    accounts = InMemoryAccounts()
    drafts = InMemoryDrafts()
    history = InMemoryHistory()
    rustest = FakeRustest()
    scores_svc = ScoresService(accounts, history, rustest)  # type: ignore[arg-type]
    auth_svc = AuthService(drafts, accounts, rustest, scores_svc)  # type: ignore[arg-type]
    session_svc = SessionService(accounts, drafts)  # type: ignore[arg-type]

    telegram_id = 401
    await _login(auth_svc, telegram_id, drafts)
    await accounts.save(
        (await accounts.get(telegram_id)).model_copy(update={"spoiler_scores": True})  # type: ignore[union-attr]
    )
    history.snapshots[telegram_id] = [make_exam(mark=70)]
    history.events[telegram_id] = []

    assert await session_svc.is_logged_in(telegram_id)
    await session_svc.clear(telegram_id)

    assert not await session_svc.is_logged_in(telegram_id)
    profile = await session_svc.get_profile(telegram_id)
    assert profile is not None
    assert profile.session_token is None
    assert profile.spoiler_scores is True
    assert history.snapshots[telegram_id]


@pytest.mark.asyncio
async def test_relogin_keeps_spoiler_preference() -> None:
    accounts = InMemoryAccounts()
    drafts = InMemoryDrafts()
    history = InMemoryHistory()
    rustest = FakeRustest()
    scores_svc = ScoresService(accounts, history, rustest)  # type: ignore[arg-type]
    auth_svc = AuthService(drafts, accounts, rustest, scores_svc)  # type: ignore[arg-type]
    session_svc = SessionService(accounts, drafts)  # type: ignore[arg-type]

    telegram_id = 402
    await _login(auth_svc, telegram_id, drafts)
    await accounts.save(
        (await accounts.get(telegram_id)).model_copy(update={"spoiler_scores": True})  # type: ignore[union-attr]
    )
    await session_svc.clear(telegram_id)

    await _login(auth_svc, telegram_id, drafts)
    account = await session_svc.get_account(telegram_id)
    assert account is not None
    assert account.has_session
    assert account.spoiler_scores is True


@pytest.mark.asyncio
async def test_watcher_expires_without_deleting_profile() -> None:
    accounts = InMemoryAccounts()
    drafts = InMemoryDrafts()
    history = InMemoryHistory()
    rustest = FakeRustest()
    scores_svc = ScoresService(accounts, history, rustest)  # type: ignore[arg-type]
    auth_svc = AuthService(drafts, accounts, rustest, scores_svc)  # type: ignore[arg-type]

    telegram_id = 403
    await _login(auth_svc, telegram_id, drafts)
    history.snapshots[telegram_id] = [make_exam()]

    account = await accounts.get(telegram_id)
    assert account is not None

    bot = AsyncMock()
    scores_svc_mock = AsyncMock()
    from egebot.domain.exam_snapshot import FetchScoresResult

    scores_svc_mock.fetch_for_account.return_value = FetchScoresResult.unauthorized()
    admin_svc = AdminService(_settings(), accounts, drafts, history)  # type: ignore[arg-type]
    watcher = ScoresWatcher(bot, _settings(), accounts, scores_svc_mock, admin_svc)

    await watcher._check_account(account)

    profile = await accounts.get(telegram_id)
    assert profile is not None
    assert profile.session_token is None
    assert telegram_id in history.snapshots
    bot.send_message.assert_awaited()
