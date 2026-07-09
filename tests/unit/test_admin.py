from unittest.mock import AsyncMock

import pytest

from egebot.config import Settings
from egebot.domain.admin import AdminStats, BroadcastResult
from egebot.services.admin import AdminService


@pytest.fixture
def admin_svc() -> AdminService:
    settings = Settings(
        TG_API_TOKEN="1:test",
        DB_NAME="egebot",
        DB_USER="postgres",
        DB_PASS="postgres",
        ADMIN_CHAT_IDS="42,99",
    )
    accounts = AsyncMock()
    drafts = AsyncMock()
    history = AsyncMock()
    accounts.count_stats.return_value = {
        "total_users": 10,
        "with_scores": 7,
        "alerts_enabled": 9,
        "spoiler_enabled": 2,
    }
    drafts.count.return_value = 1
    history.count_events.return_value = 25
    return AdminService(settings, accounts, drafts, history)


def test_is_admin(admin_svc: AdminService) -> None:
    assert admin_svc.is_admin(42)
    assert not admin_svc.is_admin(1)


@pytest.mark.asyncio
async def test_collect_stats(admin_svc: AdminService) -> None:
    stats = await admin_svc.collect_stats()
    assert stats == AdminStats(
        total_users=10,
        with_scores=7,
        alerts_enabled=9,
        spoiler_enabled=2,
        pending_auth=1,
        score_events=25,
    )


def test_format_stats_contains_numbers(admin_svc: AdminService) -> None:
    text = admin_svc.format_stats(
        AdminStats(
            total_users=3,
            with_scores=2,
            alerts_enabled=3,
            spoiler_enabled=1,
            pending_auth=0,
            score_events=4,
        )
    )
    assert "Пользователей: *3*" in text
    assert "С баллами: *2*" in text
    assert "Событий в истории: *4*" in text


def test_format_broadcast_result(admin_svc: AdminService) -> None:
    text = admin_svc.format_broadcast_result(
        BroadcastResult(total=5, sent=4, blocked=1, failed=0),
    )
    assert "Доставлено: *4*" in text
    assert "Заблокировали бота: *1*" in text
