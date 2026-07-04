from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from egebot.bot.keyboards import guest_keyboard, member_keyboard
from egebot.content import ui_copy as t
from egebot.services.session import SessionService

router = Router(name="fallback")


@router.message(F.text)
async def on_unknown_text(message: Message, session_svc: SessionService) -> None:
    user = message.from_user
    if user is None:
        return
    if await session_svc.is_logged_in(user.id):
        await message.answer(t.UNKNOWN_INPUT, reply_markup=member_keyboard())
        return
    await message.answer(
        "Чтобы начать, нажми /start или кнопку «🔐 Войти».",
        reply_markup=guest_keyboard(),
    )
