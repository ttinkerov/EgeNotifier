from __future__ import annotations

from aiogram import Bot, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from egebot.bot.filters.admin import IsAdmin
from egebot.bot.states import AdminFlow
from egebot.content import admin_copy as t
from egebot.services.admin import AdminService
from egebot.services.universities import UniversitiesService

router = Router(name="admin")
router.message.filter(IsAdmin())


@router.message(Command("stats"))
async def cmd_stats(message: Message, admin_svc: AdminService) -> None:
    stats = await admin_svc.collect_stats()
    await message.answer(admin_svc.format_stats(stats))


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminFlow.broadcast)
    await message.answer(t.ADMIN_BROADCAST_ASK)


@router.message(Command("version"))
async def cmd_version(message: Message, admin_svc: AdminService) -> None:
    await message.answer(f"EgeNotifier `{admin_svc.app_version}`")


@router.message(Command("reload_unis", "reload_catalog"))
async def cmd_reload_unis(message: Message, uni_svc: UniversitiesService) -> None:
    try:
        count = uni_svc.reload_catalog()
    except Exception as exc:  # noqa: BLE001 — show error to admin
        await message.answer(t.ADMIN_CATALOG_INVALID.format(error=exc))
        return
    await message.answer(t.ADMIN_CATALOG_RELOADED.format(count=count))


@router.message(Command("cancel"), StateFilter(AdminFlow.broadcast))
async def cmd_broadcast_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(t.ADMIN_BROADCAST_CANCELLED)


@router.message(StateFilter(AdminFlow.broadcast))
async def on_broadcast_text(message: Message, state: FSMContext, bot: Bot, admin_svc: AdminService) -> None:
    if not message.text or not message.text.strip():
        await state.clear()
        await message.answer(t.ADMIN_BROADCAST_EMPTY)
        return

    await message.answer("Рассылаю…")
    result = await admin_svc.broadcast(bot, message.text)
    await state.clear()
    await message.answer(admin_svc.format_broadcast_result(result))
