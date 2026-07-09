from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from egebot.config import Settings


class IsAdmin(BaseFilter):
    async def __call__(self, message: Message, settings: Settings) -> bool:
        user = message.from_user
        return user is not None and user.id in settings.admin_ids
