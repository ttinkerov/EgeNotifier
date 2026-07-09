from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from egebot.config import Settings
from egebot.services.admin import AdminService
from egebot.services.auth import AuthService
from egebot.services.scores import ScoresService
from egebot.services.session import SessionService
from egebot.services.settings import SettingsService
from egebot.services.universities import UniversitiesService


class DependenciesMiddleware(BaseMiddleware):
    def __init__(
        self,
        settings: Settings,
        session_svc: SessionService,
        auth_svc: AuthService,
        scores_svc: ScoresService,
        settings_svc: SettingsService,
        uni_svc: UniversitiesService,
        admin_svc: AdminService,
    ) -> None:
        self._settings = settings
        self._session_svc = session_svc
        self._auth_svc = auth_svc
        self._scores_svc = scores_svc
        self._settings_svc = settings_svc
        self._uni_svc = uni_svc
        self._admin_svc = admin_svc

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["settings"] = self._settings
        data["session_svc"] = self._session_svc
        data["auth_svc"] = self._auth_svc
        data["scores_svc"] = self._scores_svc
        data["settings_svc"] = self._settings_svc
        data["uni_svc"] = self._uni_svc
        data["admin_svc"] = self._admin_svc
        return await handler(event, data)
