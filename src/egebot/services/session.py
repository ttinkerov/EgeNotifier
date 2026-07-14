from __future__ import annotations

from aiogram.fsm.context import FSMContext

from egebot.domain.models import TgAccount
from egebot.storage.repositories.accounts import AccountRepository
from egebot.storage.repositories.auth_drafts import AuthDraftRepository


class SessionService:
    def __init__(
        self,
        accounts: AccountRepository,
        drafts: AuthDraftRepository,
    ) -> None:
        self._accounts = accounts
        self._drafts = drafts

    async def is_logged_in(self, telegram_id: int) -> bool:
        return await self._accounts.has_active_session(telegram_id)

    async def clear(self, telegram_id: int, state: FSMContext | None = None) -> None:
        """End portal session without deleting score history or prefs."""
        await self._accounts.invalidate_session(telegram_id)
        await self._drafts.delete(telegram_id)
        if state is not None:
            await state.clear()

    async def begin_auth(self, telegram_id: int, state: FSMContext) -> None:
        await self._accounts.invalidate_session(telegram_id)
        await self._drafts.start(telegram_id)
        await state.clear()

    async def get_account(self, telegram_id: int) -> TgAccount | None:
        """Active portal session only."""
        return await self._accounts.get_active(telegram_id)

    async def get_profile(self, telegram_id: int) -> TgAccount | None:
        """Account row including soft-logged-out profiles."""
        return await self._accounts.get(telegram_id)
