from __future__ import annotations

import asyncpg

from egebot.domain.models import AuthDraft


_ALLOWED_DRAFT_FIELDS = frozenset({
    "step", "name_digest", "subject_code", "document_ref", "challenge_id", "challenge_reply",
})


class AuthDraftRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get(self, telegram_id: int) -> AuthDraft | None:
        row = await self._pool.fetchrow(
            """
            SELECT telegram_id, step, name_digest, subject_code,
                   document_ref, challenge_id, challenge_reply
            FROM auth_drafts WHERE telegram_id = $1
            """,
            telegram_id,
        )
        if row is None:
            return None
        return AuthDraft.model_validate(dict(row))

    async def start(self, telegram_id: int) -> None:
        await self._pool.execute(
            """
            INSERT INTO auth_drafts (telegram_id, step)
            VALUES ($1, 'name')
            ON CONFLICT (telegram_id) DO UPDATE SET
                step = 'name',
                name_digest = NULL,
                subject_code = NULL,
                document_ref = NULL,
                challenge_id = NULL,
                challenge_reply = NULL
            """,
            telegram_id,
        )

    async def update(self, telegram_id: int, **fields: object) -> None:
        if not fields:
            return
        unknown = set(fields) - _ALLOWED_DRAFT_FIELDS
        if unknown:
            raise ValueError(f"Unknown draft fields: {unknown}")
        columns = ", ".join(f"{key} = ${i + 2}" for i, key in enumerate(fields))
        values = list(fields.values())
        await self._pool.execute(
            f"UPDATE auth_drafts SET {columns} WHERE telegram_id = $1",
            telegram_id,
            *values,
        )

    async def delete(self, telegram_id: int) -> bool:
        result = await self._pool.execute(
            "DELETE FROM auth_drafts WHERE telegram_id = $1",
            telegram_id,
        )
        return result.endswith("1")
