from unittest.mock import AsyncMock

import pytest

from egebot.config import Settings
from egebot.domain.exam_snapshot import FetchScoresResult, FetchScoresStatus
from egebot.domain.models import TgAccount
from egebot.services.watcher import ScoresWatcher


def test_database_url_hydrates_discrete_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASS", raising=False)
    settings = Settings(
        TG_API_TOKEN="1:test",
        DATABASE_URL="postgresql://alice:s3cret@db.example:6543/egenotify",
    )
    assert settings.db_user == "alice"
    assert settings.db_pass == "s3cret"
    assert settings.db_addr == "db.example"
    assert settings.db_port == 6543
    assert settings.db_name == "egenotify"
    assert settings.can_auto_create_database


def test_fetch_scores_result_is_ok() -> None:
    assert FetchScoresResult.ok([]).is_ok
    assert not FetchScoresResult.portal_down().is_ok
    assert not FetchScoresResult.unauthorized().is_ok


@pytest.mark.asyncio
async def test_watcher_marks_expired_session() -> None:
    bot = AsyncMock()
    settings = Settings(
        TG_API_TOKEN="1:test",
        DB_NAME="egebot",
        DB_USER="postgres",
        DB_PASS="postgres",
    )
    accounts = AsyncMock()
    scores_svc = AsyncMock()
    admin_svc = AsyncMock()

    account = TgAccount(telegram_id=7, subject_code=77, session_token="dead")
    scores_svc.fetch_for_account.return_value = FetchScoresResult.unauthorized()

    watcher = ScoresWatcher(bot, settings, accounts, scores_svc, admin_svc)
    failed = await watcher._check_account(account)

    assert failed is False
    accounts.delete.assert_awaited_once_with(7)
    bot.send_message.assert_awaited()
    args, kwargs = bot.send_message.await_args
    assert args[0] == 7
    assert "истекла" in args[1].lower() or "Сессия" in args[1]


@pytest.mark.asyncio
async def test_watcher_portal_down_requires_full_batch_failure() -> None:
    bot = AsyncMock()
    settings = Settings(
        TG_API_TOKEN="1:test",
        DB_NAME="egebot",
        DB_USER="postgres",
        DB_PASS="postgres",
        watcher_concurrency=2,
        poll_cooldown_sec=0,
        watcher_backoff_sec=0,
    )
    accounts = AsyncMock()
    scores_svc = AsyncMock()
    admin_svc = AsyncMock()

    subscribers = [
        TgAccount(telegram_id=i, subject_code=77, session_token="t")
        for i in range(3)
    ]
    accounts.list_with_alerts.return_value = subscribers

    outcomes = [
        FetchScoresResult.portal_down(),
        FetchScoresResult.portal_down(),
        FetchScoresResult.ok([]),
    ]

    async def fetch_side_effect(account: TgAccount) -> FetchScoresResult:
        return outcomes[account.telegram_id]

    scores_svc.fetch_for_account.side_effect = fetch_side_effect

    watcher = ScoresWatcher(bot, settings, accounts, scores_svc, admin_svc)
    await watcher._scan_all()

    admin_svc.notify_portal_down.assert_not_awaited()


@pytest.mark.asyncio
async def test_watcher_portal_down_when_all_fail() -> None:
    bot = AsyncMock()
    settings = Settings(
        TG_API_TOKEN="1:test",
        DB_NAME="egebot",
        DB_USER="postgres",
        DB_PASS="postgres",
        watcher_concurrency=3,
        poll_cooldown_sec=0,
        watcher_backoff_sec=0,
    )
    accounts = AsyncMock()
    scores_svc = AsyncMock()
    admin_svc = AsyncMock()

    subscribers = [
        TgAccount(telegram_id=i, subject_code=77, session_token="t")
        for i in range(2)
    ]
    accounts.list_with_alerts.return_value = subscribers
    scores_svc.fetch_for_account.return_value = FetchScoresResult.portal_down()

    watcher = ScoresWatcher(bot, settings, accounts, scores_svc, admin_svc)
    await watcher._scan_all()

    admin_svc.notify_portal_down.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_scores_rate_limit_is_portal_down() -> None:
    from egebot.core.rustest import RustestClient
    from unittest.mock import MagicMock

    class _FakeResponse:
        def __init__(self, status: int) -> None:
            self.status = status

        async def json(self, content_type: str | None = None) -> object:
            return {}

        async def __aenter__(self) -> "_FakeResponse":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

    settings = Settings(
        TG_API_TOKEN="1:test",
        DB_NAME="egebot",
        DB_USER="postgres",
        DB_PASS="postgres",
    )
    client = RustestClient(settings)
    session = MagicMock()
    session.get.return_value = _FakeResponse(429)
    client._http = session

    result = await client.fetch_scores("token", attempts=1)
    assert result.status is FetchScoresStatus.PORTAL_DOWN
