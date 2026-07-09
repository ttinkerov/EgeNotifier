from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

from egebot.bot.handlers import auth, callbacks, commands, fallback, menu, universities
from egebot.bot.handlers import settings as settings_handlers
from egebot.bot.middlewares import ErrorMiddleware
from egebot.bot.middlewares.auth_state import RestoreAuthStateMiddleware
from egebot.bot.middlewares.deps import DependenciesMiddleware
from egebot.config import get_settings
from egebot.core.rustest import RustestClient
from egebot.logging_setup import setup_logging
from egebot.services.auth import AuthService
from egebot.services.scores import ScoresService
from egebot.services.session import SessionService
from egebot.services.settings import SettingsService
from egebot.services.universities import UniversitiesService
from egebot.services.watcher import ScoresWatcher
from egebot.storage.database import Database, DatabaseError
from egebot.storage.repositories import AccountRepository, AuthDraftRepository, ScoreHistoryRepository


def _build_dispatcher(
    *,
    settings,
    session_svc: SessionService,
    auth_svc: AuthService,
    scores_svc: ScoresService,
    settings_svc: SettingsService,
    uni_svc: UniversitiesService,
    drafts: AuthDraftRepository,
) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(ErrorMiddleware())
    dp.update.middleware(
        DependenciesMiddleware(
            settings=settings,
            session_svc=session_svc,
            auth_svc=auth_svc,
            scores_svc=scores_svc,
            settings_svc=settings_svc,
            uni_svc=uni_svc,
        )
    )
    dp.update.middleware(RestoreAuthStateMiddleware(drafts))
    dp.include_router(commands.router)
    dp.include_router(menu.router)
    dp.include_router(universities.router)
    dp.include_router(settings_handlers.router)
    dp.include_router(callbacks.router)
    dp.include_router(auth.router)
    dp.include_router(fallback.router)
    return dp


async def _run() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    db = Database(settings)
    try:
        await db.connect()
    except DatabaseError as exc:
        logger.error("{}", exc)
        raise SystemExit(1) from exc

    rustest = RustestClient(settings)
    await rustest.open()

    accounts = AccountRepository(db.pool)
    drafts = AuthDraftRepository(db.pool)
    history = ScoreHistoryRepository(db.pool)
    scores_svc = ScoresService(accounts, history, rustest)
    session_svc = SessionService(accounts, drafts)
    auth_svc = AuthService(drafts, accounts, rustest, scores_svc)
    settings_svc = SettingsService(accounts)
    uni_svc = UniversitiesService()

    session = AiohttpSession(proxy=settings.proxy_url) if settings.proxy_url else None
    bot = Bot(
        token=settings.tg_api_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = _build_dispatcher(
        settings=settings,
        session_svc=session_svc,
        auth_svc=auth_svc,
        scores_svc=scores_svc,
        settings_svc=settings_svc,
        uni_svc=uni_svc,
        drafts=drafts,
    )

    logger.info("EgeNotifier {} is up", settings.app_version)
    watcher = ScoresWatcher(bot, settings, accounts, scores_svc)
    watcher_task = asyncio.create_task(watcher.run())
    try:
        await dp.start_polling(bot)
    finally:
        watcher_task.cancel()
        try:
            await watcher_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()
        await rustest.close()
        await db.disconnect()


def main() -> None:
    asyncio.run(_run())
