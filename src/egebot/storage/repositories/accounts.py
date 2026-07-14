from __future__ import annotations

import asyncpg

from egebot.domain.models import TgAccount
from egebot.security.crypto import FieldEncryptor


class AccountRepository:
    def __init__(self, pool: asyncpg.Pool, encryptor: FieldEncryptor | None = None) -> None:
        self._pool = pool
        self._crypto = encryptor or FieldEncryptor.noop()

    def _to_model(self, row: asyncpg.Record) -> TgAccount:
        data = dict(row)
        raw_token = data.get("session_token")
        data["session_token"] = self._crypto.decrypt(raw_token) if raw_token else None
        return TgAccount.model_validate(data)

    async def get(self, telegram_id: int) -> TgAccount | None:
        """Return profile row even if session is inactive (token cleared)."""
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
        return self._to_model(row)

    async def get_active(self, telegram_id: int) -> TgAccount | None:
        account = await self.get(telegram_id)
        if account is None or not account.has_session:
            return None
        return account

    async def has_active_session(self, telegram_id: int) -> bool:
        val = await self._pool.fetchval(
            """
            SELECT 1 FROM tg_accounts
            WHERE telegram_id = $1 AND session_token IS NOT NULL
            """,
            telegram_id,
        )
        return val is not None

    async def exists(self, telegram_id: int) -> bool:
        val = await self._pool.fetchval(
            "SELECT 1 FROM tg_accounts WHERE telegram_id = $1",
            telegram_id,
        )
        return val is not None

    async def save(self, account: TgAccount) -> None:
        token = (
            self._crypto.encrypt(account.session_token)
            if account.session_token
            else None
        )
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
                alerts_enabled = EXCLUDED.alerts_enabled,
                spoiler_scores = EXCLUDED.spoiler_scores,
                snapshot_hash = EXCLUDED.snapshot_hash,
                linked_at = NOW()
            """,
            account.telegram_id,
            account.subject_code,
            token,
            account.alerts_enabled,
            account.spoiler_scores,
            account.snapshot_hash,
        )

    async def invalidate_session(self, telegram_id: int) -> bool:
        """Clear portal session but keep profile, prefs, and score history."""
        result = await self._pool.execute(
            """
            UPDATE tg_accounts
            SET session_token = NULL
            WHERE telegram_id = $1 AND session_token IS NOT NULL
            """,
            telegram_id,
        )
        return result.endswith("1")

    async def list_with_alerts(self) -> list[TgAccount]:
        rows = await self._pool.fetch(
            """
            SELECT telegram_id, subject_code, session_token,
                   alerts_enabled, spoiler_scores, snapshot_hash
            FROM tg_accounts
            WHERE alerts_enabled = TRUE
              AND session_token IS NOT NULL
            ORDER BY linked_at
            """
        )
        return [self._to_model(row) for row in rows]

    async def list_ids(self) -> list[int]:
        rows = await self._pool.fetch(
            """
            SELECT telegram_id FROM tg_accounts
            WHERE session_token IS NOT NULL
            ORDER BY linked_at
            """
        )
        return [int(row["telegram_id"]) for row in rows]

    async def count_stats(self) -> dict[str, int]:
        row = await self._pool.fetchrow(
            """
            SELECT
                COUNT(*)::int AS total_users,
                COUNT(*) FILTER (WHERE session_token IS NOT NULL)::int AS active_sessions,
                COUNT(*) FILTER (WHERE snapshot_hash IS NOT NULL)::int AS with_scores,
                COUNT(*) FILTER (
                    WHERE alerts_enabled AND session_token IS NOT NULL
                )::int AS alerts_enabled,
                COUNT(*) FILTER (WHERE spoiler_scores)::int AS spoiler_enabled
            FROM tg_accounts
            """
        )
        assert row is not None
        return dict(row)

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
