from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from egebot.domain.models import ExamScore


class ExamDisplayStatus(str, Enum):
    NONE = "none"
    WAITING = "waiting"
    HIDDEN = "hidden"
    PRELIMINARY = "preliminary"
    PUBLISHED = "published"
    COMPOSITION_PASS = "composition_pass"
    COMPOSITION_FAIL = "composition_fail"


class ScoreChangeEvent(BaseModel):
    exam_id: int
    subject: str
    old_status: ExamDisplayStatus = ExamDisplayStatus.NONE
    new_status: ExamDisplayStatus
    old_mark: int | None = None
    new_mark: int | None = None
    recorded_at: datetime | None = None


class StoredScoreChangeEvent(ScoreChangeEvent):
    id: int


def exam_display_status(exam: ExamScore) -> ExamDisplayStatus:
    if exam.is_hidden:
        return ExamDisplayStatus.HIDDEN
    if exam.is_composition:
        if not exam.mark and not exam.has_result:
            return ExamDisplayStatus.WAITING
        return (
            ExamDisplayStatus.COMPOSITION_PASS
            if exam.mark == 1
            else ExamDisplayStatus.COMPOSITION_FAIL
        )
    if exam.has_result:
        return ExamDisplayStatus.PUBLISHED
    if exam.mark:
        return ExamDisplayStatus.PRELIMINARY
    return ExamDisplayStatus.WAITING


def _state_tuple(exam: ExamScore) -> tuple[ExamDisplayStatus, int | None]:
    status = exam_display_status(exam)
    if status in (ExamDisplayStatus.WAITING, ExamDisplayStatus.HIDDEN, ExamDisplayStatus.NONE):
        return status, None
    return status, exam.mark


def diff_snapshots(
    old: list[ExamScore],
    new: list[ExamScore],
) -> list[ScoreChangeEvent]:
    old_map = {exam.exam_id: exam for exam in old}
    events: list[ScoreChangeEvent] = []

    for exam in new:
        previous = old_map.get(exam.exam_id)
        new_status, new_mark = _state_tuple(exam)

        if previous is None:
            if new_status in (ExamDisplayStatus.WAITING, ExamDisplayStatus.HIDDEN):
                continue
            events.append(
                ScoreChangeEvent(
                    exam_id=exam.exam_id,
                    subject=exam.subject,
                    old_status=ExamDisplayStatus.NONE,
                    new_status=new_status,
                    new_mark=new_mark,
                )
            )
            continue

        old_status, old_mark = _state_tuple(previous)
        if (old_status, old_mark) == (new_status, new_mark):
            continue

        events.append(
            ScoreChangeEvent(
                exam_id=exam.exam_id,
                subject=exam.subject,
                old_status=old_status,
                new_status=new_status,
                old_mark=old_mark,
                new_mark=new_mark,
            )
        )

    return events


def exams_from_payload(payload: list[dict[str, object]]) -> list[ExamScore]:
    return [ExamScore.model_validate(item) for item in payload]


def exams_to_payload(exams: list[ExamScore]) -> list[dict[str, object]]:
    return [exam.model_dump(by_alias=True) for exam in exams]
