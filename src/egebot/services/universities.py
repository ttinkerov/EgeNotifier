from __future__ import annotations

from egebot.content.university_catalog import load_programs, reload_programs
from egebot.domain.universities import (
    FundingType,
    MatchResult,
    StudyField,
    UniversityProgram,
    UserScores,
)

_NEAR_MARGIN = -100
_DEFAULT_LIMIT = 20


def _probability(margin: int) -> tuple[int, str]:
    if margin >= 30:
        return 92, "очень высокая"
    if margin >= 20:
        return 82, "высокая"
    if margin >= 10:
        return 68, "хорошая"
    if margin >= 5:
        return 52, "реальная"
    if margin >= 0:
        return 35, "на грани"
    if margin >= -15:
        return 28, "почти проходишь"
    if margin >= -30:
        return 18, "мало шансов"
    if margin >= -50:
        return 12, "маловероятно"
    if margin >= _NEAR_MARGIN:
        return 6, "очень маловероятно"
    return 0, ""


class UniversitiesService:
    def reload_catalog(self) -> int:
        return len(reload_programs())

    def catalog_size(self) -> int:
        return len(load_programs())

    def find_best(
        self,
        scores: UserScores,
        *,
        funding: FundingType | None,
        region_code: int | None,
        field: StudyField,
        limit: int = _DEFAULT_LIMIT,
    ) -> list[MatchResult]:
        if not scores.subjects:
            return []

        candidates: list[MatchResult] = []
        for program in load_programs():
            if program.field != field:
                continue
            if funding is not None and program.funding != funding:
                continue
            if region_code is not None and program.region_code != region_code:
                continue
            match = self._evaluate(scores, program)
            if match is not None:
                candidates.append(match)

        candidates.sort(
            key=lambda item: (item.margin >= 0, item.probability, item.program.rating, item.margin),
            reverse=True,
        )
        return candidates[:limit]

    @staticmethod
    def _evaluate(scores: UserScores, program: UniversityProgram) -> MatchResult | None:
        if not all(subject in scores.subjects for subject in program.counted_subjects):
            return None

        for subject, minimum in program.subject_mins.items():
            if scores.subjects[subject] < minimum:
                return None

        user_total = scores.total_for(program.counted_subjects)
        margin = user_total - program.passing_total
        probability, label = _probability(margin)
        if probability == 0:
            return None

        return MatchResult(
            program=program,
            user_total=user_total,
            margin=margin,
            probability=probability,
            probability_label=label,
        )
