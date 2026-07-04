from __future__ import annotations

from egebot.content import ui_copy as t
from egebot.storage.repositories.accounts import AccountRepository


class SettingsService:
    def __init__(self, accounts: AccountRepository) -> None:
        self._accounts = accounts

    async def get_panel(self, telegram_id: int) -> tuple[str, bool] | None:
        account = await self._accounts.get(telegram_id)
        if account is None:
            return None
        return t.settings_text(account.spoiler_scores), account.spoiler_scores

    async def toggle_spoiler(self, telegram_id: int) -> tuple[bool, str] | None:
        new_value = await self._accounts.toggle_spoiler_scores(telegram_id)
        if new_value is None:
            return None
        return new_value, t.settings_text(new_value)
