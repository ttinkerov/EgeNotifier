from datetime import date

from egebot.domain.exam_snapshot import (
    FetchScoresStatus,
    compute_snapshot_hash,
    has_published_scores,
)
from egebot.domain.models import ExamScore


def _exam(**overrides: object) -> ExamScore:
    data: dict[str, object] = {
        "ExamId": 1,
        "Subject": "Русский язык",
        "ExamDate": date(2025, 5, 27),
        "IsComposition": False,
        "IsHidden": False,
        "HasResult": True,
        "TestMark": 80,
        "MinMark": 36,
    }
    data.update(overrides)
    return ExamScore.model_validate(data)


def test_snapshot_hash_is_stable() -> None:
    exams = [_exam()]
    assert compute_snapshot_hash(exams) == compute_snapshot_hash(exams)


def test_snapshot_hash_changes_when_mark_changes() -> None:
    first = [_exam(TestMark=80)]
    second = [_exam(TestMark=81)]
    assert compute_snapshot_hash(first) != compute_snapshot_hash(second)


def test_has_published_scores() -> None:
    assert has_published_scores([_exam()])
    assert not has_published_scores([_exam(HasResult=False, TestMark=0)])


def test_fetch_scores_status_values() -> None:
    assert FetchScoresStatus.OK.value == "ok"
