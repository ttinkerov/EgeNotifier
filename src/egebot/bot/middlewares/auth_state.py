from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject

from egebot.bot.states import AuthFlow
from egebot.services.session import SessionService
from egebot.storage.repositories.auth_drafts import AuthDraftRepository

_STEP_TO_STATE = {
    "name": AuthFlow.name,
    "region": AuthFlow.region,
    "document": AuthFlow.document,
    "captcha": AuthFlow.captcha,
    "login": AuthFlow.captcha,
}


class RestoreAuthStateMiddleware(BaseMiddleware):
    def __init__(self, drafts: AuthDraftRepository) -> None:
        self._drafts = drafts

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user is not None:
            state: FSMContext | None = data.get("state")
            session_svc: SessionService | None = data.get("session_svc")
            if (
                state is not None
                and await state.get_state() is None
                and (
                    session_svc is None
                    or not await session_svc.is_logged_in(event.from_user.id)
                )
            ):
                draft = await self._drafts.get(event.from_user.id)
                if draft is not None:
                    auth_state = _STEP_TO_STATE.get(draft.step)
                    if auth_state is not None:
                        await state.set_state(auth_state)
        return await handler(event, data)
