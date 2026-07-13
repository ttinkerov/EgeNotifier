from unittest.mock import AsyncMock

import pytest
from aiogram.fsm.storage.base import StorageKey

from egebot.storage.fsm import PostgresFSMStorage


def _key(user_id: int = 1) -> StorageKey:
    return StorageKey(bot_id=42, chat_id=user_id, user_id=user_id)


@pytest.mark.asyncio
async def test_fsm_set_get_state() -> None:
    pool = AsyncMock()
    pool.fetchval = AsyncMock(return_value="AuthFlow:name")
    storage = PostgresFSMStorage(pool)

    await storage.set_state(_key(), "AuthFlow:name")
    assert await storage.get_state(_key()) == "AuthFlow:name"
    pool.execute.assert_awaited()


@pytest.mark.asyncio
async def test_fsm_set_get_data() -> None:
    pool = AsyncMock()
    pool.fetchval = AsyncMock(return_value={"uni_field": "it"})
    storage = PostgresFSMStorage(pool)

    await storage.set_data(_key(), {"uni_field": "it"})
    assert await storage.get_data(_key()) == {"uni_field": "it"}


@pytest.mark.asyncio
async def test_fsm_state_update_does_not_stomp_data() -> None:
    pool = AsyncMock()
    storage = PostgresFSMStorage(pool)
    await storage.set_state(_key(), "AdminFlow:broadcast")
    sql = pool.execute.await_args.args[0]
    assert "EXCLUDED.state" in sql
    assert "data = EXCLUDED.data" not in sql
