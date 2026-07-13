from __future__ import annotations

from html import escape

from egebot.core.rustest import RustestClient
from egebot.domain.exam_snapshot import (
    FetchScoresResult,
    FetchScoresStatus,
    compute_snapshot_hash,
)
from egebot.domain.models import ExamScore, TgAccount
from egebot.domain.score_history import (
    ExamDisplayStatus,
    ScoreChangeEvent,
    StoredScoreChangeEvent,
    diff_snapshots,
)
from egebot.storage.repositories.accounts import AccountRepository
from egebot.storage.repositories.score_history import ScoreHistoryRepository

SCORES_PARSE_MODE = "HTML"
_HISTORY_LIMIT = 40


def _mark_label(mark: int, subject: str) -> str:
    if "математ" in subject.lower().replace("ё", "е") and "базов" in subject.lower().replace("ё", "е"):
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
    lowered = subject.lower().replace("ё", "е")
    if "устн" in lowered or ("математ" in lowered and "базов" in lowered):
        return ""
    return " ✅" if mark >= threshold else " ❗️"


def _format_mark(text: str, *, spoiler: bool) -> str:
    safe = escape(text)
    if spoiler:
        return f"<tg-spoiler>{safe}</tg-spoiler>"
    return f"<b>{safe}</b>"


def _format_mark_value(mark: int | None, subject: str) -> str:
    if mark is None:
        return "—"
    lowered = subject.lower().replace("ё", "е")
    if "математ" in lowered and "базов" in lowered:
        return str(mark)
    if "устн" in lowered or "сочин" in lowered:
        return "зачёт" if mark == 1 else "незачёт"
    return f"{mark}{_mark_label(mark, subject)}".strip()


def _format_status_value(status: ExamDisplayStatus, mark: int | None, subject: str) -> str:
    if status is ExamDisplayStatus.WAITING:
        return "ожидается"
    if status is ExamDisplayStatus.HIDDEN:
        return "скрыт"
    if status is ExamDisplayStatus.COMPOSITION_PASS:
        return "зачёт"
    if status is ExamDisplayStatus.COMPOSITION_FAIL:
        return "незачёт"
    if status is ExamDisplayStatus.PRELIMINARY and mark is not None:
        return f"{_format_mark_value(mark, subject)} (предварительно)"
    if mark is not None:
        return _format_mark_value(mark, subject)
    return "—"


def format_change_line(event: ScoreChangeEvent, *, spoiler: bool = False) -> str:
    subject = escape(event.subject)
    old_status = event.old_status
    new_status = event.new_status

    if old_status is ExamDisplayStatus.NONE:
        value = _format_status_value(new_status, event.new_mark, event.subject)
        text = f"{subject}: появился результат — {value}"
        return f"• {_format_mark(text, spoiler=spoiler)}"

    old_value = _format_status_value(old_status, event.old_mark, event.subject)
    new_value = _format_status_value(new_status, event.new_mark, event.subject)

    if old_value == new_value:
        text = f"{subject}: обновление"
    else:
        text = f"{subject}: {old_value} → {new_value}"

    return f"• {_format_mark(text, spoiler=spoiler)}"


def _format_change_timestamp(recorded_at) -> str:
    return recorded_at.strftime("%d.%m %H:%M")


class ScoresService:
    def __init__(
        self,
        accounts: AccountRepository,
        history: ScoreHistoryRepository,
        rustest: RustestClient,
    ) -> None:
        self._accounts = accounts
        self._history = history
        self._rustest = rustest

    async def fetch_for_user(self, telegram_id: int) -> FetchScoresResult:
        account = await self._accounts.get(telegram_id)
        if account is None:
            return FetchScoresResult.unauthorized()
        return await self.fetch_for_account(account)

    async def fetch_for_account(self, account: TgAccount) -> FetchScoresResult:
        return await self._rustest.fetch_scores(account.session_token)

    async def sync_snapshot(
        self,
        telegram_id: int,
        exams: list[ExamScore],
        *,
        snapshot_hash: str | None = None,
    ) -> list[ScoreChangeEvent]:
        new_hash = snapshot_hash if snapshot_hash is not None else compute_snapshot_hash(exams)
        account = await self._accounts.get(telegram_id)
        if account is not None and account.snapshot_hash == new_hash:
            stored = await self._history.get_snapshot(telegram_id)
            if stored is not None:
                return []

        old_exams = await self._history.get_snapshot(telegram_id)
        if old_exams is None and account is not None and account.snapshot_hash == new_hash:
            await self._history.save_snapshot(telegram_id, exams, new_hash)
            return []

        changes = diff_snapshots(old_exams or [], exams)
        if changes:
            await self._history.insert_events(telegram_id, changes)

        await self._history.save_snapshot(telegram_id, exams, new_hash)
        await self._accounts.update_snapshot(telegram_id, new_hash)
        return changes

    async def render(
        self,
        telegram_id: int,
        exams: list[ExamScore],
        *,
        account: TgAccount | None = None,
        highlight_updates: bool = False,
        changes: list[ScoreChangeEvent] | None = None,
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
            if changes:
                lines.append("<b>Изменения:</b>")
                for event in changes:
                    lines.append(format_change_line(event, spoiler=use_spoiler))
                lines.append("")
            lines.append("<b>Твои баллы:</b>\n")
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
                    if not exam.is_grade_only:
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

        if persist_snapshot and account:
            await self.sync_snapshot(
                telegram_id,
                exams,
                snapshot_hash=snapshot_hash,
            )

        return "\n".join(lines)

    async def render_history(self, telegram_id: int) -> str:
        account = await self._accounts.get(telegram_id)
        use_spoiler = account.spoiler_scores if account else False
        events = await self._history.list_events(telegram_id, limit=_HISTORY_LIMIT)
        if not events:
            return (
                "<b>📈 История баллов</b>\n\n"
                "<i>Пока нет записей. История появится, когда баллы изменятся.</i>"
            )

        lines = ["<b>📈 История баллов</b>\n"]
        for event in events:
            timestamp = _format_change_timestamp(event.recorded_at)
            line = format_change_line(event, spoiler=use_spoiler)
            lines.append(f"<i>{timestamp}</i> — {line.removeprefix('• ')}")

        return "\n".join(lines)

    async def seed_snapshot(self, telegram_id: int, exams: list[ExamScore]) -> None:
        await self.sync_snapshot(telegram_id, exams)
