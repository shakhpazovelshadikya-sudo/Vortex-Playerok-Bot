from __future__ import annotations

import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

router = Router(name="chats")


def setup(app):
    async def _run(fn, *a, **kw):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*a, **kw))

    @router.message(Command("chats"))
    @router.callback_query(F.data == "menu:chats")
    async def chats_list(event):
        is_cb = isinstance(event, CallbackQuery)
        user_id = event.from_user.id
        if not app.is_admin(user_id):
            return
        chats = await _run(app.pk_client.account.get_chats, 15)
        if not chats.chats:
            text = "Чатов пока нет."
            await (event.message.answer(text) if is_cb else event.answer(text))
            if is_cb:
                await event.answer()
            return
        for c in chats.chats:
            other = next((u for u in c.users if u.username != app.pk_client.account.username), None)
            uname = other.username if other else "?"
            btn = app.kb.chat_quick_actions(c.id)
            txt = f"💬 <code>{c.id}</code>\n👤 {uname}"
            if is_cb:
                await event.message.answer(txt, reply_markup=btn)
            else:
                await event.answer(txt, reply_markup=btn)
        if is_cb:
            await event.answer()

    @router.callback_query(F.data.startswith("chat:open:"))
    async def chat_open(cb: CallbackQuery):
        chat_id = cb.data.split(":", 2)[2]
        msgs = await _run(app.pk_client.account.get_chat_messages, chat_id, 15)
        lines = [f"💬 <b>История чата</b> <code>{chat_id}</code>\n"]
        for m in reversed(msgs.messages):
            who = "🧑 Покупатель" if (m.user and m.user.username != app.pk_client.account.username) else "🌀 Вы"
            text_ = getattr(m, "text", "") or "[вложение]"
            lines.append(f"{who}: {text_}")
        await cb.message.answer("\n".join(lines)[-3900:], reply_markup=app.kb.chat_quick_actions(chat_id))
        await cb.answer()

    @router.callback_query(F.data.startswith("chat:reply:"))
    async def chat_reply(cb: CallbackQuery):
        chat_id = cb.data.split(":", 2)[2]
        app.pending.set(cb.from_user.id, "reply_to_chat", chat_id=chat_id)
        await cb.message.answer(
            "✍️ Напиши текст ответа (или пришли фото/GIF). /cancel — отмена."
        )
        await cb.answer()

    @router.callback_query(F.data.startswith("chat:templates:"))
    async def chat_templates(cb: CallbackQuery):
        chat_id = cb.data.split(":", 2)[2]
        tpls = app.templates.all()
        if not tpls:
            await cb.answer("Нет сохранённых заготовок. Добавь через /templates", show_alert=True)
            return
        await cb.message.answer("Выбери заготовку:", reply_markup=app.kb.templates_list(tpls, chat_id))
        await cb.answer()

    @router.callback_query(F.data.startswith("tpl:use:"))
    async def tpl_use(cb: CallbackQuery):
        _, _, tpl_id, chat_id = cb.data.split(":", 3)
        tpl = app.templates.get(int(tpl_id))
        if not tpl:
            await cb.answer("Заготовка не найдена", show_alert=True)
            return
        await app.send_playerok_message(chat_id, tpl["text"])
        await cb.answer("Отправлено ✅")

    @router.message(Command("cancel"))
    async def cancel_cmd(message: Message):
        app.pending.clear(message.from_user.id)
        await message.answer("Отменено.")

    app.dp.include_router(router)
