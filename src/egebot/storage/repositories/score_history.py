from __future__ import annotations

import json

import asyncpg

from egebot.domain.models import ExamScore
from egebot.domain.score_history import (
    ExamDisplayStatus,
    ScoreChangeEvent,
    StoredScoreChangeEvent,
    exams_from_payload,
    exams_to_payload,
)


class ScoreHistoryRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_snapshot(self, telegram_id: int) -> list[ExamScore] | None:
        row = await self._pool.fetchrow(
            """
            SELECT payload
            FROM score_snapshots
            WHERE telegram_id = $1
            """,
            telegram_id,
        )
        if row is None:
            return None
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return exams_from_payload(list(payload))

    async def save_snapshot(
        self,
        telegram_id: int,
        exams: list[ExamScore],
        snapshot_hash: str,
    ) -> None:
        await self._pool.execute(
            """
            INSERT INTO score_snapshots (telegram_id, snapshot_hash, payload, updated_at)
            VALUES ($1, $2, $3::jsonb, NOW())
            ON CONFLICT (telegram_id) DO UPDATE SET
                snapshot_hash = EXCLUDED.snapshot_hash,
                payload = EXCLUDED.payload,
                updated_at = NOW()
            """,
            telegram_id,
            snapshot_hash,
            json.dumps(exams_to_payload(exams)),
        )

    async def insert_events(
        self,
        telegram_id: int,
        events: list[ScoreChangeEvent],
    ) -> None:
        if not events:
            return
        await self._pool.executemany(
            """
            INSERT INTO score_change_events (
                telegram_id, exam_id, subject,
                old_status, new_status, old_mark, new_mark
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            [
                (
                    telegram_id,
                    event.exam_id,
                    event.subject,
                    event.old_status.value,
                    event.new_status.value,
                    event.old_mark,
                    event.new_mark,
                )
                for event in events
            ],
        )

    async def list_events(
        self,
        telegram_id: int,
        *,
        limit: int = 40,
    ) -> list[StoredScoreChangeEvent]:
        rows = await self._pool.fetch(
            """
            SELECT id, exam_id, subject, old_status, new_status,
                   old_mark, new_mark, recorded_at
            FROM score_change_events
            WHERE telegram_id = $1
            ORDER BY recorded_at DESC, id DESC
            LIMIT $2
            """,
            telegram_id,
            limit,
        )
        return [
            StoredScoreChangeEvent(
                id=row["id"],
                exam_id=row["exam_id"],
                subject=row["subject"],
                old_status=ExamDisplayStatus(row["old_status"]),
                new_status=ExamDisplayStatus(row["new_status"]),
                old_mark=row["old_mark"],
                new_mark=row["new_mark"],
                recorded_at=row["recorded_at"],
            )
            for row in rows
        ]

    async def delete_for_user(self, telegram_id: int) -> None:
        await self._pool.execute(
            "DELETE FROM score_change_events WHERE telegram_id = $1",
            telegram_id,
        )
        await self._pool.execute(
            "DELETE FROM score_snapshots WHERE telegram_id = $1",
            telegram_id,
        )
