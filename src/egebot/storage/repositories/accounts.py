from __future__ import annotations

import asyncpg

from egebot.domain.models import TgAccount


class AccountRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get(self, telegram_id: int) -> TgAccount | None:
        row = await self._pool.fetchrow(
            """
            SELECT telegram_id, subject_code, session_token,
                   alerts_enabled, spoiler_scores, snapshot_hash
            FROM tg_accounts WHERE telegram_id = $1
            """,
            telegram_id,
        )
        if row is None:
            return None
        return TgAccount.model_validate(dict(row))

    async def exists(self, telegram_id: int) -> bool:
        val = await self._pool.fetchval(
            "SELECT 1 FROM tg_accounts WHERE telegram_id = $1",
            telegram_id,
        )
        return val is not None

    async def save(self, account: TgAccount) -> None:
        await self._pool.execute(
            """
            INSERT INTO tg_accounts (
                telegram_id, subject_code, session_token,
                alerts_enabled, spoiler_scores, snapshot_hash
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (telegram_id) DO UPDATE SET
                subject_code = EXCLUDED.subject_code,
                session_token = EXCLUDED.session_token,
                linked_at = NOW()
            """,
            account.telegram_id,
            account.subject_code,
            account.session_token,
            account.alerts_enabled,
            account.spoiler_scores,
            account.snapshot_hash,
        )

    async def list_with_alerts(self) -> list[TgAccount]:
        rows = await self._pool.fetch(
            """
            SELECT telegram_id, subject_code, session_token,
                   alerts_enabled, spoiler_scores, snapshot_hash
            FROM tg_accounts
            WHERE alerts_enabled = TRUE
            ORDER BY linked_at
            """
        )
        return [TgAccount.model_validate(dict(row)) for row in rows]

    async def set_alerts_enabled(self, telegram_id: int, enabled: bool) -> None:
        await self._pool.execute(
            "UPDATE tg_accounts SET alerts_enabled = $2 WHERE telegram_id = $1",
            telegram_id,
            enabled,
        )

    async def toggle_spoiler_scores(self, telegram_id: int) -> bool | None:
        row = await self._pool.fetchrow(
            """
            UPDATE tg_accounts
            SET spoiler_scores = NOT spoiler_scores
            WHERE telegram_id = $1
            RETURNING spoiler_scores
            """,
            telegram_id,
        )
        if row is None:
            return None
        return bool(row["spoiler_scores"])

    async def update_snapshot(self, telegram_id: int, snapshot_hash: str) -> None:
        await self._pool.execute(
            "UPDATE tg_accounts SET snapshot_hash = $2 WHERE telegram_id = $1",
            telegram_id,
            snapshot_hash,
        )

    async def delete(self, telegram_id: int) -> bool:
        result = await self._pool.execute(
            "DELETE FROM tg_accounts WHERE telegram_id = $1",
            telegram_id,
        )
        return result.endswith("1")
