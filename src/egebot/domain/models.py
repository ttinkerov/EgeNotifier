from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class SignInStatus(str, Enum):
    OK = "ok"
    BAD_CREDENTIALS = "bad_credentials"
    PORTAL_ERROR = "portal_error"
    TIMEOUT = "timeout"


class ExamScore(BaseModel):
    exam_id: int = Field(alias="ExamId")
    subject: str = Field(alias="Subject")
    exam_date: date = Field(alias="ExamDate")
    is_composition: bool = Field(alias="IsComposition")
    is_hidden: bool = Field(alias="IsHidden")
    has_result: bool = Field(alias="HasResult")
    mark: int = Field(alias="TestMark")
    min_mark: int = Field(alias="MinMark")

    model_config = {"populate_by_name": True}


class TgAccount(BaseModel):
    telegram_id: int
    subject_code: int
    session_token: str
    alerts_enabled: bool = True
    spoiler_scores: bool = False
    snapshot_hash: str | None = None


class AuthDraft(BaseModel):
    telegram_id: int
    step: str
    name_digest: str | None = None
    subject_code: int | None = None
    document_ref: str | None = None
    challenge_id: str | None = None
    challenge_reply: str | None = None
