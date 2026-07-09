from datetime import date

import pytest

from egebot.domain.models import ExamScore, TgAccount
from egebot.services.scores import ScoresService


def _exam(subject: str, mark: int) -> ExamScore:
    return ExamScore.model_validate({
        "ExamId": 1,
        "Subject": subject,
        "ExamDate": date(2025, 5, 27),
        "IsComposition": False,
        "IsHidden": False,
        "HasResult": True,
        "TestMark": mark,
        "MinMark": 36,
    })


@pytest.mark.asyncio
async def test_render_sum_excludes_basic_math() -> None:
    service = ScoresService(accounts=None, history=None, rustest=None)  # type: ignore[arg-type]
    exams = [
        _exam("Русский язык", 90),
        _exam("Математика базовая", 5),
        _exam("Английский язык", 90),
        _exam("Обществознание", 70),
    ]

    text = await service.render(
        telegram_id=1,
        exams=exams,
        account=TgAccount(telegram_id=1, subject_code=77, session_token="x"),
        persist_snapshot=False,
    )

    assert "Сумма:" in text
    assert "250 баллов" in text
    assert "255" not in text


def test_basic_math_is_grade_only() -> None:
    assert _exam("Математика базовая", 5).is_grade_only
    assert not _exam("Математика профильная", 64).is_grade_only
