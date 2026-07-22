from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router(name="blacklist_ui")


def setup(app):
    @router.message(Command("blacklist"))
    @router.callback_query(F.data == "menu:blacklist")
    async def list_bl(event):
        is_cb = isinstance(event, CallbackQuery)
        rows = app.blacklist.all()
        b = InlineKeyboardBuilder()
        lines = ["🚫 <b>Чёрный список</b>\n"]
        if not rows:
            lines.append("Пусто.")
        for r in rows:
            lines.append(f"@{r['username']} — {r['reason'] or 'без причины'}")
            b.button(text=f"✅ Убрать @{r['username']}", callback_data=f"bl:del:{r['username']}")
        b.button(text="➕ Добавить в ЧС", callback_data="bl:add")
        b.button(text="◀️ Назад", callback_data="menu:main")
        b.adjust(1)
        text = "\n".join(lines)
        markup = b.as_markup()
        if is_cb:
            await event.message.edit_text(text, reply_markup=markup)
            await event.answer()
        else:
            await event.answer(text, reply_markup=markup)

    @router.callback_query(F.data == "bl:add")
    async def add_bl(cb: CallbackQuery):
        app.pending.set(cb.from_user.id, "add_blacklist_user")
        await cb.message.answer("Пришли username покупателя, которого нужно занести в ЧС:")
        await cb.answer()

    @router.callback_query(F.data.startswith("bl:del:"))
    async def del_bl(cb: CallbackQuery):
        uname = cb.data.split(":", 2)[2]
        app.blacklist.remove(uname)
        await cb.answer("Убран из ЧС ✅")
        await list_bl(cb)

    app.dp.include_router(router)
