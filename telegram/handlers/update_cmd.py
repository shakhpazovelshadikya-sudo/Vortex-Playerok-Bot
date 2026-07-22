from __future__ import annotations

import asyncio
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.updater import Updater, UpdateError

router = Router(name="update")
logger = logging.getLogger("update_cmd")


def setup(app):
    updater = Updater(repo_dir=".")

    async def _run(fn, *a, **kw):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*a, **kw))

    async def _check_and_report(message_or_cb):
        is_cb = isinstance(message_or_cb, CallbackQuery)
        target = message_or_cb.message if is_cb else message_or_cb

        await target.answer("🔎 Проверяю обновления на GitHub...")
        try:
            has_update, local, remote = await _run(updater.check_for_updates)
        except UpdateError as e:
            await target.answer(f"⚠️ {e}")
            if is_cb:
                await message_or_cb.answer()
            return

        if not has_update:
            await target.answer(f"✅ Уже последняя версия (<code>{local}</code>). Обновлений нет.")
            if is_cb:
                await message_or_cb.answer()
            return

        b = InlineKeyboardBuilder()
        b.button(text="⬇️ Обновить и перезапустить", callback_data="update:confirm")
        b.button(text="❌ Отмена", callback_data="update:cancel")
        b.adjust(1)
        await target.answer(
            f"🆕 <b>Доступно обновление</b>\n"
            f"Сейчас: <code>{local}</code> → доступно: <code>{remote}</code>\n\n"
            f"⚠️ Твои данные (config.yaml, база данных, логи) не тронутся — "
            f"обновится только код бота. После обновления бот автоматически "
            f"перезапустится (это займёт несколько секунд).",
            reply_markup=b.as_markup(),
        )
        if is_cb:
            await message_or_cb.answer()

    @router.message(Command("update"))
    async def update_cmd(message: Message):
        if not app.is_admin(message.from_user.id):
            return
        await _check_and_report(message)

    @router.callback_query(F.data == "update:check")
    async def update_check_cb(cb: CallbackQuery):
        if not app.is_admin(cb.from_user.id):
            await cb.answer()
            return
        await _check_and_report(cb)

    @router.callback_query(F.data == "update:cancel")
    async def update_cancel(cb: CallbackQuery):
        await cb.message.edit_text("Отменено. Данные и код бота не изменены.")
        await cb.answer()

    @router.callback_query(F.data == "update:confirm")
    async def update_confirm(cb: CallbackQuery):
        if not app.is_admin(cb.from_user.id):
            await cb.answer()
            return
        await cb.message.edit_text("⏳ Обновляю бота, не выключай сервер...")
        try:
            log_text = await _run(updater.pull_and_upgrade)
        except UpdateError as e:
            await cb.message.answer(f"❌ Обновление не удалось:\n\n{e}")
            await cb.answer()
            return

        short_log = log_text[-3500:]
        await cb.message.answer(
            f"✅ Обновление установлено.\n<pre>{short_log}</pre>\n\n🔄 Перезапускаюсь..."
        )
        await cb.answer()
        logger.info("Перезапуск после обновления через /update")
        await asyncio.sleep(1)
        updater.restart_process()

    app.dp.include_router(router)
