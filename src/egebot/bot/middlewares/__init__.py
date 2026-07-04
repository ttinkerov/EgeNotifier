from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from loguru import logger


class ErrorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception:
            logger.exception("Handler error for {}", type(event).__name__)
            if isinstance(event, Message):
                await event.answer("Что-то пошло не так. Попробуй /start или /help.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Ошибка. Попробуй ещё раз.", show_alert=True)
            return None
