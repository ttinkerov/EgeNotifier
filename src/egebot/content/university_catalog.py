from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from egebot.domain.models import ExamScore
from egebot.domain.universities import UniversityProgram, UserScores

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "universities.json"

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
    if "базов" in lowered and "математ" in lowered:
        return None
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
        if exam.is_grade_only or exam.is_composition or (not exam.has_result and not exam.mark):
            continue
        key = normalize_subject_name(exam.subject)
        if key is None:
            continue
        subjects[key] = max(subjects.get(key, 0), exam.mark)
    return UserScores(subjects=subjects)


def parse_programs(raw: object) -> tuple[UniversityProgram, ...]:
    if not isinstance(raw, list):
        raise ValueError("Каталог должен быть JSON-массивом программ")
    if not raw:
        raise ValueError("Каталог пуст")
    programs = tuple(UniversityProgram.model_validate(item) for item in raw)
    ids = [program.id for program in programs]
    if len(ids) != len(set(ids)):
        raise ValueError("В каталоге есть дублирующиеся id программ")
    return programs


def load_programs_from_path(path: Path) -> tuple[UniversityProgram, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return parse_programs(raw)


@lru_cache
def load_programs() -> tuple[UniversityProgram, ...]:
    return load_programs_from_path(CATALOG_PATH)


def reload_programs() -> tuple[UniversityProgram, ...]:
    load_programs.cache_clear()
    return load_programs()


def write_catalog(programs: tuple[UniversityProgram, ...] | list[UniversityProgram], path: Path) -> int:
    payload = [program.model_dump(mode="json") for program in programs]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if path.resolve() == CATALOG_PATH.resolve():
        reload_programs()
    return len(payload)


def update_catalog_from_file(source: Path, *, dest: Path | None = None) -> int:
    target = dest or CATALOG_PATH
    programs = load_programs_from_path(source)
    return write_catalog(programs, target)
