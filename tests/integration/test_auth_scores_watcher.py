from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from egebot.config import Settings
from egebot.domain.exam_snapshot import compute_snapshot_hash
from egebot.domain.models import SignInStatus
from egebot.services.admin import AdminService
from egebot.services.auth import AuthService
from egebot.services.scores import ScoresService
from egebot.services.watcher import ScoresWatcher
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


@pytest.mark.asyncio
async def test_auth_scores_watcher_notifies_on_change() -> None:
    accounts = InMemoryAccounts()
    drafts = InMemoryDrafts()
    history = InMemoryHistory()
    rustest = FakeRustest()
    scores_svc = ScoresService(accounts, history, rustest)  # type: ignore[arg-type]
    auth_svc = AuthService(drafts, accounts, rustest, scores_svc)  # type: ignore[arg-type]

    telegram_id = 101
    await drafts.start(telegram_id)
    assert await auth_svc.save_name(telegram_id, "Иванов Иван")
    ok, _ = await auth_svc.save_region(telegram_id, "77")
    assert ok
    assert await auth_svc.save_document(telegram_id, "123456")
    captcha = await auth_svc.request_captcha(telegram_id)
    assert captcha is not None
    assert await auth_svc.save_captcha_answer(telegram_id, "123456")

    status, exams = await auth_svc.complete_login(telegram_id)
    assert status is SignInStatus.OK
    assert exams is not None
    account = await accounts.get(telegram_id)
    assert account is not None
    assert account.session_token == "session-token"
    assert account.snapshot_hash == compute_snapshot_hash(exams)

    rustest.scores = [make_exam(mark=95)]
    bot = AsyncMock()
    settings = _settings()
    admin_svc = AdminService(settings, accounts, drafts, history)  # type: ignore[arg-type]
    watcher = ScoresWatcher(bot, settings, accounts, scores_svc, admin_svc)  # type: ignore[arg-type]

    failed = await watcher._check_account(account)
    assert failed is False
    bot.send_message.assert_awaited()
    args, _kwargs = bot.send_message.await_args
    assert args[0] == telegram_id
    assert "95" in args[1] or "балл" in args[1].lower()

    refreshed = await accounts.get(telegram_id)
    assert refreshed is not None
    assert refreshed.snapshot_hash == compute_snapshot_hash(rustest.scores)


@pytest.mark.asyncio
async def test_watcher_ignores_unchanged_scores() -> None:
    accounts = InMemoryAccounts()
    drafts = InMemoryDrafts()
    history = InMemoryHistory()
    rustest = FakeRustest()
    scores_svc = ScoresService(accounts, history, rustest)  # type: ignore[arg-type]
    auth_svc = AuthService(drafts, accounts, rustest, scores_svc)  # type: ignore[arg-type]

    telegram_id = 202
    await drafts.start(telegram_id)
    await auth_svc.save_name(telegram_id, "Петров Пётр")
    await auth_svc.save_region(telegram_id, "77")
    await auth_svc.save_document(telegram_id, "654321")
    await auth_svc.request_captcha(telegram_id)
    await auth_svc.save_captcha_answer(telegram_id, "654321")
    await auth_svc.complete_login(telegram_id)

    account = await accounts.get(telegram_id)
    assert account is not None

    bot = AsyncMock()
    settings = _settings()
    admin_svc = AdminService(settings, accounts, drafts, history)  # type: ignore[arg-type]
    watcher = ScoresWatcher(bot, settings, accounts, scores_svc, admin_svc)  # type: ignore[arg-type]

    await watcher._check_account(account)
    bot.send_message.assert_not_awaited()
