from __future__ import annotations

from html import escape

from egebot.core.rustest import RustestClient
from egebot.domain.exam_snapshot import (
    FetchScoresResult,
    FetchScoresStatus,
    compute_snapshot_hash,
)
from egebot.domain.models import ExamScore, TgAccount
from egebot.storage.repositories.accounts import AccountRepository

SCORES_PARSE_MODE = "HTML"


def _mark_label(mark: int, subject: str) -> str:
    if "Математика базовая" in subject:
        return ""
    n = mark % 10
    if mark % 100 in (11, 12, 13, 14):
        return " баллов"
    if n == 1:
        return " балл"
    if 2 <= n <= 4:
        return " балла"
    return " баллов"


def _threshold_icon(mark: int, threshold: int, subject: str) -> str:
    if "устн" in subject.lower():
        return ""
    return " ✅" if mark >= threshold else " ❗️"


def _format_mark(text: str, *, spoiler: bool) -> str:
    safe = escape(text)
    if spoiler:
        return f"<tg-spoiler>{safe}</tg-spoiler>"
    return f"<b>{safe}</b>"


class ScoresService:
    def __init__(self, accounts: AccountRepository, rustest: RustestClient) -> None:
        self._accounts = accounts
        self._rustest = rustest

    async def fetch_for_user(self, telegram_id: int) -> FetchScoresResult:
        account = await self._accounts.get(telegram_id)
        if account is None:
            return FetchScoresResult.unauthorized()
        return await self.fetch_for_account(account)

    async def fetch_for_account(self, account: TgAccount) -> FetchScoresResult:
        exams = await self._rustest.fetch_scores(account.session_token)
        if exams is None:
            return FetchScoresResult.portal_down()
        if not exams:
            return FetchScoresResult.empty()
        return FetchScoresResult.ok(exams)

    async def render(
        self,
        telegram_id: int,
        exams: list[ExamScore],
        *,
        account: TgAccount | None = None,
        highlight_updates: bool = False,
        persist_snapshot: bool = True,
        snapshot_hash: str | None = None,
    ) -> str:
        if account is None:
            account = await self._accounts.get(telegram_id)
        use_spoiler = account.spoiler_scores if account else False
        total = 0
        show_total = True
        lines: list[str] = []

        if highlight_updates:
            lines.append("<b>⚡ Есть обновления</b>\n")
        else:
            lines.append("<b>Твои баллы:</b>\n")

        for exam in exams:
            subject = escape(exam.subject)
            if exam.has_result and not exam.is_hidden:
                if exam.is_composition:
                    raw = "Зачёт ✅" if exam.mark == 1 else "Незачёт ❗️"
                    mark_text = _format_mark(raw, spoiler=use_spoiler)
                else:
                    raw = (
                        f"{exam.mark}{_mark_label(exam.mark, exam.subject)}"
                        f"{_threshold_icon(exam.mark, exam.min_mark, exam.subject)}"
                    )
                    mark_text = _format_mark(raw.strip(), spoiler=use_spoiler)
                    total += exam.mark
            elif exam.mark:
                raw = (
                    f"{exam.mark}{_mark_label(exam.mark, exam.subject)}"
                    f"{_threshold_icon(exam.mark, exam.min_mark, exam.subject)}"
                )
                mark_text = f"{_format_mark(raw.strip(), spoiler=use_spoiler)} <i>(предварительно)</i>"
                show_total = False
            else:
                mark_text = "<i>ожидается</i>"
                show_total = False

            lines.append(f"{subject} — {mark_text}")

        if show_total and total:
            sum_text = f"{total}{_mark_label(total, '')}"
            lines.append(f"\n<i>Сумма:</i> {_format_mark(sum_text, spoiler=use_spoiler)}")

        new_hash = snapshot_hash if snapshot_hash is not None else compute_snapshot_hash(exams)
        if persist_snapshot and account and account.snapshot_hash != new_hash:
            await self._accounts.update_snapshot(telegram_id, new_hash)

        return "\n".join(lines)

    async def seed_snapshot(self, telegram_id: int, exams: list[ExamScore]) -> None:
        await self._accounts.update_snapshot(telegram_id, compute_snapshot_hash(exams))
