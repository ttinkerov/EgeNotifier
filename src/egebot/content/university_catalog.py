from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from egebot.domain.models import ExamScore
from egebot.domain.universities import UniversityProgram, UserScores

_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "universities.json"

SUBJECT_LABELS: dict[str, str] = {
    "russian": "Русский язык",
    "math": "Математика (проф.)",
    "informatics": "Информатика",
    "physics": "Физика",
    "chemistry": "Химия",
    "biology": "Биология",
    "social": "Обществознание",
    "history": "История",
    "literature": "Литература",
    "geography": "География",
    "foreign": "Иностранный язык",
}

_SUBJECT_PATTERNS: list[tuple[str, str]] = [
    (r"информат|кегэ", "informatics"),
    (r"русск", "russian"),
    (r"математ", "math"),
    (r"физик", "physics"),
    (r"хими", "chemistry"),
    (r"биолог", "biology"),
    (r"обществ", "social"),
    (r"истори", "history"),
    (r"литерат", "literature"),
    (r"географ", "geography"),
    (r"иностр|англ|нем|франц", "foreign"),
]

_MANUAL_ALIASES: dict[str, str] = {
    "рус": "russian",
    "русский": "russian",
    "мат": "math",
    "матем": "math",
    "математика": "math",
    "инф": "informatics",
    "информатика": "informatics",
    "физ": "physics",
    "физика": "physics",
    "хим": "chemistry",
    "химия": "chemistry",
    "био": "biology",
    "биология": "biology",
    "общ": "social",
    "обществознание": "social",
    "ист": "history",
    "история": "history",
    "лит": "literature",
    "литература": "literature",
}


def normalize_subject_name(name: str) -> str | None:
    lowered = name.lower().replace("ё", "е")
    for pattern, key in _SUBJECT_PATTERNS:
        if re.search(pattern, lowered):
            return key
    for alias, key in sorted(_MANUAL_ALIASES.items(), key=lambda item: -len(item[0])):
        if re.search(rf"(?<![а-яa-z]){re.escape(alias)}", lowered):
            return key
    return None


def scores_from_exams(exams: list[ExamScore]) -> UserScores:
    subjects: dict[str, int] = {}
    for exam in exams:
        if exam.is_composition or (not exam.has_result and not exam.mark):
            continue
        key = normalize_subject_name(exam.subject)
        if key is None:
            continue
        subjects[key] = max(subjects.get(key, 0), exam.mark)
    return UserScores(subjects=subjects)


@lru_cache
def load_programs() -> tuple[UniversityProgram, ...]:
    raw = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    return tuple(UniversityProgram.model_validate(item) for item in raw)
