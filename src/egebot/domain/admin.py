from __future__ import annotations

from pydantic import BaseModel, Field


class AdminStats(BaseModel):
    total_users: int = 0
    with_scores: int = 0
    alerts_enabled: int = 0
    spoiler_enabled: int = 0
    pending_auth: int = 0
    score_events: int = 0


class BroadcastResult(BaseModel):
    total: int = 0
    sent: int = 0
    blocked: int = 0
    failed: int = 0
    errors: list[str] = Field(default_factory=list)
