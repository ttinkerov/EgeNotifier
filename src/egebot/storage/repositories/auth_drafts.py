from __future__ import annotations

import asyncpg

from egebot.domain.models import AuthDraft
from egebot.security.crypto import FieldEncryptor


_ALLOWED_DRAFT_FIELDS = frozenset({
    "step", "name_digest", "subject_code", "document_ref", "challenge_id", "challenge_reply",
})
_ENCRYPTED_FIELDS = frozenset({"document_ref"})


class AuthDraftRepository:
    def __init__(self, pool: asyncpg.Pool, encryptor: FieldEncryptor | None = None) -> None:
        self._pool = pool
        self._crypto = encryptor or FieldEncryptor.noop()

    def _to_model(self, row: asyncpg.Record) -> AuthDraft:
        data = dict(row)
        data["document_ref"] = self._crypto.decrypt(data.get("document_ref"))
        return AuthDraft.model_validate(data)

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
        return self._to_model(row)

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

        prepared: dict[str, object] = {}
        for key, value in fields.items():
            if key in _ENCRYPTED_FIELDS and isinstance(value, str):
                prepared[key] = self._crypto.encrypt(value)
            else:
                prepared[key] = value

        columns = ", ".join(f"{key} = ${i + 2}" for i, key in enumerate(prepared))
        values = list(prepared.values())
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

    async def count(self) -> int:
        value = await self._pool.fetchval("SELECT COUNT(*)::int FROM auth_drafts")
        return int(value or 0)
