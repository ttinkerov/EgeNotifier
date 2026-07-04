from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FundingType(str, Enum):
    BUDGET = "budget"
    PAID = "paid"


class StudyField(str, Enum):
    IT = "it"
    ENGINEERING = "engineering"
    MEDICINE = "medicine"
    ECONOMICS = "economics"
    LAW = "law"
    HUMANITIES = "humanities"
    PEDAGOGY = "pedagogy"


STUDY_FIELD_LABELS: dict[StudyField, str] = {
    StudyField.IT: "💻 IT и программирование",
    StudyField.ENGINEERING: "⚙️ Инженерия",
    StudyField.MEDICINE: "🩺 Медицина",
    StudyField.ECONOMICS: "📈 Экономика и менеджмент",
    StudyField.LAW: "⚖️ Право",
    StudyField.HUMANITIES: "📚 Гуманитарные науки",
    StudyField.PEDAGOGY: "🎓 Педагогика",
}


class UniversityProgram(BaseModel):
    id: str
    university: str
    program: str
    city: str
    region_code: int
    field: StudyField
    funding: FundingType
    passing_total: int
    subject_mins: dict[str, int] = Field(default_factory=dict)
    counted_subjects: list[str] = Field(default_factory=list)
    rating: int = Field(ge=1, le=100, default=50)


class MatchResult(BaseModel):
    program: UniversityProgram
    user_total: int
    margin: int
    probability: int
    probability_label: str


class UserScores(BaseModel):
    subjects: dict[str, int]

    def get(self, key: str, default: int = 0) -> int:
        return self.subjects.get(key, default)

    def total_for(self, keys: list[str]) -> int:
        return sum(self.subjects.get(key, 0) for key in keys)
