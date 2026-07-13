from __future__ import annotations

from datetime import date

from egebot.core.rustest import CaptchaPayload
from egebot.domain.exam_snapshot import FetchScoresResult
from egebot.domain.models import AuthDraft, ExamScore, SignInStatus, TgAccount
from egebot.domain.score_history import (
    ScoreChangeEvent,
    StoredScoreChangeEvent,
    exams_from_payload,
    exams_to_payload,
)


def make_exam(
    exam_id: int = 1,
    subject: str = "Русский язык",
    mark: int = 80,
    *,
    has_result: bool = True,
) -> ExamScore:
    return ExamScore.model_validate({
        "ExamId": exam_id,
        "Subject": subject,
        "ExamDate": date(2025, 5, 27),
        "IsComposition": False,
        "IsHidden": False,
        "HasResult": has_result,
        "TestMark": mark,
        "MinMark": 36,
    })


class InMemoryAccounts:
    def __init__(self) -> None:
        self.items: dict[int, TgAccount] = {}

    async def get(self, telegram_id: int) -> TgAccount | None:
        return self.items.get(telegram_id)

    async def exists(self, telegram_id: int) -> bool:
        return telegram_id in self.items

    async def save(self, account: TgAccount) -> None:
        self.items[account.telegram_id] = account

    async def list_with_alerts(self) -> list[TgAccount]:
        return [a for a in self.items.values() if a.alerts_enabled]

    async def list_ids(self) -> list[int]:
        return list(self.items)

    async def set_alerts_enabled(self, telegram_id: int, enabled: bool) -> None:
        account = self.items.get(telegram_id)
        if account is None:
            return
        self.items[telegram_id] = account.model_copy(update={"alerts_enabled": enabled})

    async def update_snapshot(self, telegram_id: int, snapshot_hash: str) -> None:
        account = self.items.get(telegram_id)
        if account is None:
            return
        self.items[telegram_id] = account.model_copy(update={"snapshot_hash": snapshot_hash})

    async def delete(self, telegram_id: int) -> bool:
        return self.items.pop(telegram_id, None) is not None


class InMemoryDrafts:
    def __init__(self) -> None:
        self.items: dict[int, AuthDraft] = {}

    async def get(self, telegram_id: int) -> AuthDraft | None:
        return self.items.get(telegram_id)

    async def start(self, telegram_id: int) -> None:
        self.items[telegram_id] = AuthDraft(telegram_id=telegram_id, step="name")

    async def update(self, telegram_id: int, **fields: object) -> None:
        current = self.items.get(telegram_id)
        if current is None:
            current = AuthDraft(telegram_id=telegram_id, step="name")
        self.items[telegram_id] = current.model_copy(update=fields)

    async def delete(self, telegram_id: int) -> bool:
        return self.items.pop(telegram_id, None) is not None


class InMemoryHistory:
    def __init__(self) -> None:
        self.snapshots: dict[int, list[ExamScore]] = {}
        self.events: dict[int, list[ScoreChangeEvent]] = {}

    async def get_snapshot(self, telegram_id: int) -> list[ExamScore] | None:
        exams = self.snapshots.get(telegram_id)
        if exams is None:
            return None
        return exams_from_payload(exams_to_payload(exams))

    async def save_snapshot(
        self,
        telegram_id: int,
        exams: list[ExamScore],
        snapshot_hash: str,
    ) -> None:
        self.snapshots[telegram_id] = list(exams)

    async def insert_events(self, telegram_id: int, events: list[ScoreChangeEvent]) -> None:
        self.events.setdefault(telegram_id, []).extend(events)

    async def list_events(
        self,
        telegram_id: int,
        *,
        limit: int = 40,
    ) -> list[StoredScoreChangeEvent]:
        rows = self.events.get(telegram_id, [])
        return [
            StoredScoreChangeEvent(id=index + 1, **event.model_dump())
            for index, event in enumerate(rows[:limit])
        ]


class FakeRustest:
    def __init__(self) -> None:
        self.token = "session-token"
        self.scores: list[ExamScore] = [make_exam(mark=70)]
        self.sign_in_status = SignInStatus.OK

    async def fetch_captcha(self) -> CaptchaPayload:
        return CaptchaPayload(challenge_id="chal", image=b"img")

    async def sign_in(self, draft: AuthDraft) -> tuple[SignInStatus, str | None]:
        if self.sign_in_status is SignInStatus.OK:
            return SignInStatus.OK, self.token
        return self.sign_in_status, None

    async def fetch_scores(self, session_token: str, *, attempts: int = 3) -> FetchScoresResult:
        if session_token != self.token:
            return FetchScoresResult.unauthorized()
        if not self.scores:
            return FetchScoresResult.empty()
        return FetchScoresResult.ok(list(self.scores))
