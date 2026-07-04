from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum

from egebot.domain.models import ExamScore


class FetchScoresStatus(str, Enum):
    OK = "ok"
    UNAUTHORIZED = "unauthorized"
    PORTAL_DOWN = "portal_down"
    EMPTY = "empty"


@dataclass(frozen=True, slots=True)
class FetchScoresResult:
    status: FetchScoresStatus
    exams: list[ExamScore]

    @classmethod
    def unauthorized(cls) -> FetchScoresResult:
        return cls(FetchScoresStatus.UNAUTHORIZED, [])

    @classmethod
    def portal_down(cls) -> FetchScoresResult:
        return cls(FetchScoresStatus.PORTAL_DOWN, [])

    @classmethod
    def empty(cls) -> FetchScoresResult:
        return cls(FetchScoresStatus.EMPTY, [])

    @classmethod
    def ok(cls, exams: list[ExamScore]) -> FetchScoresResult:
        return cls(FetchScoresStatus.OK, exams)


def compute_snapshot_hash(exams: list[ExamScore]) -> str:
    payload = [exam.model_dump(by_alias=True) for exam in exams]
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()


def has_published_scores(exams: list[ExamScore]) -> bool:
    return any(exam.has_result or exam.mark for exam in exams)
