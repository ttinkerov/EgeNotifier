from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from loguru import logger

from egebot.config import Settings
from egebot.content import admin_copy as t
from egebot.domain.admin import AdminStats, BroadcastResult
from egebot.storage.repositories.accounts import AccountRepository
from egebot.storage.repositories.auth_drafts import AuthDraftRepository
from egebot.storage.repositories.score_history import ScoreHistoryRepository


class AdminService:
    def __init__(
        self,
        settings: Settings,
        accounts: AccountRepository,
        drafts: AuthDraftRepository,
        history: ScoreHistoryRepository,
    ) -> None:
        self._settings = settings
        self._accounts = accounts
        self._drafts = drafts
        self._history = history

    def is_admin(self, telegram_id: int) -> bool:
        return telegram_id in self._settings.admin_ids

    async def collect_stats(self) -> AdminStats:
        account_stats = await self._accounts.count_stats()
        return AdminStats(
            total_users=account_stats["total_users"],
            with_scores=account_stats["with_scores"],
            alerts_enabled=account_stats["alerts_enabled"],
            spoiler_enabled=account_stats["spoiler_enabled"],
            pending_auth=await self._drafts.count(),
            score_events=await self._history.count_events(),
        )

    def format_stats(self, stats: AdminStats) -> str:
        return t.format_stats(
            version=self._settings.app_version,
            total_users=stats.total_users,
            with_scores=stats.with_scores,
            alerts_enabled=stats.alerts_enabled,
            spoiler_enabled=stats.spoiler_enabled,
            pending_auth=stats.pending_auth,
            score_events=stats.score_events,
        )

    async def broadcast(self, bot: Bot, text: str) -> BroadcastResult:
        recipients = await self._accounts.list_ids()
        result = BroadcastResult(total=len(recipients))

        for telegram_id in recipients:
            try:
                await bot.send_message(telegram_id, text)
                result.sent += 1
            except TelegramForbiddenError:
                result.blocked += 1
                await self._accounts.set_alerts_enabled(telegram_id, False)
            except TelegramBadRequest as exc:
                result.failed += 1
                if len(result.errors) < 5:
                    result.errors.append(f"{telegram_id}: {exc}")
                logger.warning("Broadcast failed for {}: {}", telegram_id, exc)

        return result

    def format_broadcast_result(self, result: BroadcastResult) -> str:
        lines = [
            t.format_broadcast_result(
                sent=result.sent,
                blocked=result.blocked,
                failed=result.failed,
                total=result.total,
            )
        ]
        if result.errors:
            lines.append("\n_Примеры ошибок:_")
            lines.extend(f"• `{error}`" for error in result.errors)
        return "\n".join(lines)

    async def notify_portal_down(self, bot: Bot, failures: int) -> None:
        text = t.ADMIN_PORTAL_DOWN.format(failures=failures)
        await self._notify_admins(bot, text)

    async def notify_portal_recovered(self, bot: Bot) -> None:
        await self._notify_admins(bot, t.ADMIN_PORTAL_RECOVERED)

    async def _notify_admins(self, bot: Bot, text: str) -> None:
        for admin_id in self._settings.admin_ids:
            try:
                await bot.send_message(admin_id, text)
            except (TelegramForbiddenError, TelegramBadRequest) as exc:
                logger.warning("Cannot notify admin {}: {}", admin_id, exc)
