from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from loguru import logger

from egebot.bot.keyboards import refresh_scores as refresh_scores_kb
from egebot.config import Settings
from egebot.domain.exam_snapshot import (
    FetchScoresStatus,
    compute_snapshot_hash,
    has_published_scores,
)
from egebot.domain.models import ExamScore, TgAccount
from egebot.services.admin import AdminService
from egebot.services.scores import SCORES_PARSE_MODE, ScoresService
from egebot.storage.repositories.accounts import AccountRepository


class ScoresWatcher:
    def __init__(
        self,
        bot: Bot,
        settings: Settings,
        accounts: AccountRepository,
        scores_svc: ScoresService,
        admin_svc: AdminService,
    ) -> None:
        self._bot = bot
        self._cfg = settings
        self._accounts = accounts
        self._scores = scores_svc
        self._admin = admin_svc
        self._portal_down_notified = False

    async def run(self) -> None:
        logger.info("Scores watcher started")
        try:
            while True:
                await self._scan_all()
                await asyncio.sleep(self._cfg.watcher_tick_sec)
        except asyncio.CancelledError:
            logger.info("Scores watcher stopped")
            raise

    async def _scan_all(self) -> None:
        subscribers = await self._accounts.list_with_alerts()
        if not subscribers:
            await asyncio.sleep(max(self._cfg.watcher_tick_sec, 30.0))
            return

        concurrency = max(1, self._cfg.watcher_concurrency)
        semaphore = asyncio.Semaphore(concurrency)
        portal_errors = 0
        errors_lock = asyncio.Lock()

        async def check_with_limit(account: TgAccount) -> bool:
            async with semaphore:
                failed = await self._check_account(account)
                nonlocal portal_errors
                async with errors_lock:
                    if failed:
                        portal_errors += 1
                    else:
                        portal_errors = 0
                await asyncio.sleep(self._cfg.poll_cooldown_sec)
                return failed

        await asyncio.gather(*(check_with_limit(account) for account in subscribers))

        if portal_errors >= 3:
            if not self._portal_down_notified:
                await self._admin.notify_portal_down(self._bot, portal_errors)
                self._portal_down_notified = True
            logger.warning(
                "Portal unreachable, backing off {}s",
                self._cfg.watcher_backoff_sec,
            )
            await asyncio.sleep(self._cfg.watcher_backoff_sec)
        elif self._portal_down_notified:
            await self._admin.notify_portal_recovered(self._bot)
            self._portal_down_notified = False

    async def _check_account(self, account: TgAccount) -> bool:
        result = await self._scores.fetch_for_account(account)
        if result.status is FetchScoresStatus.PORTAL_DOWN:
            return True
        if result.status is not FetchScoresStatus.OK:
            return False

        exams = result.exams
        new_hash = compute_snapshot_hash(exams)
        old_hash = account.snapshot_hash

        if old_hash is None:
            if has_published_scores(exams):
                await self._notify(account, exams, new_hash)
            else:
                await self._scores.sync_snapshot(
                    account.telegram_id,
                    exams,
                    snapshot_hash=new_hash,
                )
            return False

        if old_hash == new_hash:
            return False

        await self._notify(account, exams, new_hash)
        return False

    async def _notify(self, account: TgAccount, exams: list[ExamScore], new_hash: str) -> None:
        changes = await self._scores.sync_snapshot(
            account.telegram_id,
            exams,
            snapshot_hash=new_hash,
        )
        text = await self._scores.render(
            account.telegram_id,
            exams,
            account=account,
            highlight_updates=True,
            changes=changes,
            persist_snapshot=False,
            snapshot_hash=new_hash,
        )
        try:
            await self._bot.send_message(
                account.telegram_id,
                text,
                parse_mode=SCORES_PARSE_MODE,
                reply_markup=refresh_scores_kb(),
            )
        except TelegramForbiddenError:
            logger.info("User {} blocked the bot, disabling alerts", account.telegram_id)
            await self._accounts.set_alerts_enabled(account.telegram_id, False)
            return
        except TelegramBadRequest as exc:
            logger.warning("Cannot notify user {}: {}", account.telegram_id, exc)
            return

        logger.info("Score update sent to {}", account.telegram_id)
