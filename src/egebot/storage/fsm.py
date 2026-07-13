from __future__ import annotations

import json
from typing import Any

import asyncpg
from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StorageKey


class PostgresFSMStorage(BaseStorage):
    """Persist aiogram FSM state/data in PostgreSQL via asyncpg."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def set_state(self, key: StorageKey, state: State | str | None = None) -> None:
        state_value = state.state if isinstance(state, State) else state
        await self._pool.execute(
            """
            INSERT INTO fsm_storage (bot_id, chat_id, user_id, destiny, state, data)
            VALUES ($1, $2, $3, $4, $5, '{}'::jsonb)
            ON CONFLICT (bot_id, chat_id, user_id, destiny) DO UPDATE SET
                state = EXCLUDED.state,
                updated_at = NOW()
            """,
            key.bot_id,
            key.chat_id,
            key.user_id,
            key.destiny,
            state_value,
        )

    async def get_state(self, key: StorageKey) -> str | None:
        return await self._pool.fetchval(
            """
            SELECT state FROM fsm_storage
            WHERE bot_id = $1 AND chat_id = $2 AND user_id = $3 AND destiny = $4
            """,
            key.bot_id,
            key.chat_id,
            key.user_id,
            key.destiny,
        )

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        payload = json.dumps(data, ensure_ascii=False, default=str)
        await self._pool.execute(
            """
            INSERT INTO fsm_storage (bot_id, chat_id, user_id, destiny, state, data)
            VALUES ($1, $2, $3, $4, NULL, $5::jsonb)
            ON CONFLICT (bot_id, chat_id, user_id, destiny) DO UPDATE SET
                data = EXCLUDED.data,
                updated_at = NOW()
            """,
            key.bot_id,
            key.chat_id,
            key.user_id,
            key.destiny,
            payload,
        )

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        raw = await self._pool.fetchval(
            """
            SELECT data FROM fsm_storage
            WHERE bot_id = $1 AND chat_id = $2 AND user_id = $3 AND destiny = $4
            """,
            key.bot_id,
            key.chat_id,
            key.user_id,
            key.destiny,
        )
        if raw is None:
            return {}
        if isinstance(raw, str):
            return dict(json.loads(raw))
        return dict(raw)

    async def close(self) -> None:
        return None
