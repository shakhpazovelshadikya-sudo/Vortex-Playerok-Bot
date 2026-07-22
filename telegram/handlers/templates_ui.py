from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router(name="templates_ui")


def setup(app):
    @router.message(Command("templates"))
    @router.callback_query(F.data == "menu:templates")
    async def list_templates(event):
        is_cb = isinstance(event, CallbackQuery)
        tpls = app.templates.all()
        b = InlineKeyboardBuilder()
        lines = ["✉️ <b>Заготовки быстрых ответов</b>\n"]
        if not tpls:
            lines.append("Пока пусто.")
        for t in tpls:
            lines.append(f"#{t['id']} • {t['title']}")
            b.button(text=f"🗑 #{t['id']}", callback_data=f"tpl:del:{t['id']}")
        b.button(text="➕ Добавить заготовку", callback_data="tpl:add")
        b.button(text="◀️ Назад", callback_data="menu:main")
        b.adjust(1)
        text = "\n".join(lines)
        markup = b.as_markup()
        if is_cb:
            await event.message.edit_text(text, reply_markup=markup)
            await event.answer()
        else:
            await event.answer(text, reply_markup=markup)

    @router.callback_query(F.data == "tpl:add")
    async def add_template(cb: CallbackQuery):
        app.pending.set(cb.from_user.id, "add_template_title")
        await cb.message.answer("Как назвать заготовку? (например «Приветствие»)")
        await cb.answer()

    @router.callback_query(F.data.startswith("tpl:del:"))
    async def del_template(cb: CallbackQuery):
        tpl_id = int(cb.data.split(":")[2])
        app.templates.remove(tpl_id)
        await cb.answer("Удалено ✅")
        await list_templates(cb)

    # ---------------- пользовательские команды в чате Playerok ----------------
    @router.message(Command("commands"))
    async def list_commands(message: Message):
        rows = app.custom_commands.all()
        b = InlineKeyboardBuilder()
        lines = ["🤖 <b>Команды покупателя в чате</b>\n"]
        if not rows:
            lines.append("Пока пусто.")
        for r in rows:
            lines.append(f"#{r['id']} • {r['command']}")
            b.button(text=f"🗑 #{r['id']}", callback_data=f"cmd:del:{r['id']}")
        b.button(text="➕ Добавить команду", callback_data="cmd:add")
        b.adjust(1)
        await message.answer("\n".join(lines), reply_markup=b.as_markup())

    @router.callback_query(F.data == "cmd:add")
    async def add_command(cb: CallbackQuery):
        app.pending.set(cb.from_user.id, "add_command_name")
        await cb.message.answer(
            "Напиши команду, которую должен ввести покупатель в чате (например <code>!правила</code>):"
        )
        await cb.answer()

    @router.callback_query(F.data.startswith("cmd:del:"))
    async def del_command(cb: CallbackQuery):
        cmd_id = int(cb.data.split(":")[2])
        row = app.db.fetchone("SELECT command FROM custom_commands WHERE id=?", (cmd_id,))
        if row:
            app.custom_commands.remove(row["command"])
        await cb.answer("Удалено ✅")

    app.dp.include_router(router)
