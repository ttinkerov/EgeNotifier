from datetime import date

from egebot.domain.models import ExamScore
from egebot.domain.score_history import ExamDisplayStatus, diff_snapshots
from egebot.services.scores import format_change_line


def _exam(subject: str, mark: int, **overrides: object) -> ExamScore:
    data: dict[str, object] = {
        "ExamId": overrides.pop("exam_id", 1),
        "Subject": subject,
        "ExamDate": date(2025, 5, 27),
        "IsComposition": False,
        "IsHidden": False,
        "HasResult": True,
        "TestMark": mark,
        "MinMark": 36,
    }
    data.update(overrides)
    return ExamScore.model_validate(data)


def test_diff_detects_mark_change() -> None:
    old = [_exam("Русский язык", 85, exam_id=10)]
    new = [_exam("Русский язык", 90, exam_id=10)]
    events = diff_snapshots(old, new)
    assert len(events) == 1
    assert events[0].old_mark == 85
    assert events[0].new_mark == 90
    assert events[0].new_status is ExamDisplayStatus.PUBLISHED


def test_diff_detects_initial_result() -> None:
    old = [_exam("Русский язык", 0, HasResult=False, TestMark=0, exam_id=10)]
    new = [_exam("Русский язык", 90, exam_id=10)]
    events = diff_snapshots(old, new)
    assert len(events) == 1
    assert events[0].old_status is ExamDisplayStatus.WAITING
    assert events[0].new_mark == 90


def test_diff_ignores_unchanged_exams() -> None:
    exams = [_exam("Русский язык", 90, exam_id=10)]
    assert diff_snapshots(exams, exams) == []


def test_diff_detects_preliminary_to_published() -> None:
    old = [_exam("Обществознание", 70, HasResult=False, exam_id=11)]
    new = [_exam("Обществознание", 70, HasResult=True, exam_id=11)]
    events = diff_snapshots(old, new)
    assert len(events) == 1
    assert events[0].old_status is ExamDisplayStatus.PRELIMINARY
    assert events[0].new_status is ExamDisplayStatus.PUBLISHED


def test_format_change_line_shows_arrow() -> None:
  events = diff_snapshots(
      [_exam("Русский язык", 85, exam_id=10)],
      [_exam("Русский язык", 90, exam_id=10)],
  )
  line = format_change_line(events[0], spoiler=False)
  assert "85" in line
  assert "90" in line
  assert "→" in line


def test_diff_initial_snapshot_from_empty() -> None:
    new = [
        _exam("Русский язык", 90, exam_id=10),
        _exam("Математика базовая", 5, exam_id=11),
    ]
    events = diff_snapshots([], new)
    assert len(events) == 2
    assert all(event.old_status is ExamDisplayStatus.NONE for event in events)
