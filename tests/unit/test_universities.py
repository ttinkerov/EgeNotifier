from datetime import date

from egebot.content.university_catalog import normalize_subject_name, scores_from_exams
from egebot.domain.models import ExamScore
from egebot.domain.universities import FundingType, StudyField, UserScores
from egebot.services.universities import UniversitiesService


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


def test_scores_from_exams_all_subjects() -> None:
    exams = [
        _exam("Русский язык", 64),
        _exam("Математика профильная", 64),
        _exam("Информатика (КЕГЭ)", 72),
        _exam("Обществознание", 80),
    ]
    scores = scores_from_exams(exams)
    assert scores.get("russian") == 64
    assert scores.get("math") == 64
    assert scores.get("informatics") == 72
    assert scores.get("social") == 80
    assert len(scores.subjects) == 4


def test_four_subjects_match_it_and_economics() -> None:
    svc = UniversitiesService()
    scores = UserScores(
        subjects={
            "russian": 85,
            "math": 85,
            "informatics": 90,
            "social": 88,
        },
    )
    it_results = svc.find_best(
        scores,
        funding=FundingType.PAID,
        region_code=None,
        field=StudyField.IT,
        limit=5,
    )
    econ_results = svc.find_best(
        scores,
        funding=FundingType.PAID,
        region_code=None,
        field=StudyField.ECONOMICS,
        limit=5,
    )
    assert it_results
    assert econ_results


def test_find_it_programs_moscow_budget() -> None:
    svc = UniversitiesService()
    scores = UserScores(subjects={"russian": 85, "math": 95, "informatics": 100})
    results = svc.find_best(
        scores,
        funding=FundingType.BUDGET,
        region_code=77,
        field=StudyField.IT,
        limit=5,
    )
    assert results
    assert results[0].probability >= 35
    assert results[0].program.region_code == 77


def test_informatics_not_confused_with_math() -> None:
    assert normalize_subject_name("Информатика (КЕГЭ)") == "informatics"
    assert normalize_subject_name("Математика профильная") == "math"
    assert normalize_subject_name("Математика базовая") is None


def test_basic_math_excluded_from_university_scores() -> None:
    exams = [
        _exam("Русский язык", 90),
        _exam("Математика базовая", 5),
        _exam("Английский язык", 90),
        _exam("Обществознание", 70),
    ]
    scores = scores_from_exams(exams)
    assert scores.get("russian") == 90
    assert scores.get("foreign") == 90
    assert scores.get("social") == 70
    assert "math" not in scores.subjects
    assert scores.total_for(["russian", "foreign", "social"]) == 250


def test_typical_user_scores_find_programs() -> None:
    svc = UniversitiesService()
    scores = UserScores(subjects={"russian": 64, "math": 64, "informatics": 72})
    results = svc.find_best(
        scores,
        funding=FundingType.PAID,
        region_code=None,
        field=StudyField.IT,
    )
    assert results
    assert results[0].margin >= -100


def test_200_points_finds_novosibirsk() -> None:
    svc = UniversitiesService()
    scores = UserScores(subjects={"russian": 67, "math": 67, "informatics": 66})
    results = svc.find_best(
        scores,
        funding=None,
        region_code=54,
        field=StudyField.IT,
    )
    assert results
    cities = {item.program.city for item in results}
    assert "Новосибирск" in cities
    assert any(item.program.university == "НГУ" for item in results)


def test_no_match_very_low_scores() -> None:
    svc = UniversitiesService()
    scores = UserScores(subjects={"russian": 40, "math": 40, "informatics": 40})
    results = svc.find_best(
        scores,
        funding=FundingType.BUDGET,
        region_code=77,
        field=StudyField.IT,
    )
    assert not results


def test_missing_required_subject_no_match() -> None:
    svc = UniversitiesService()
    scores = UserScores(subjects={"russian": 90, "math": 90, "social": 90})
    results = svc.find_best(
        scores,
        funding=None,
        region_code=None,
        field=StudyField.IT,
    )
    assert not results
