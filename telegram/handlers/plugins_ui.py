from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router(name="plugins_ui")


def setup(app):
    @router.message(Command("plugins"))
    @router.callback_query(F.data == "menu:plugins")
    async def plugins_menu(event):
        is_cb = isinstance(event, CallbackQuery)
        names = app.plugins.list_names()
        b = InlineKeyboardBuilder()
        text = "🧩 <b>Плагины</b>\n\n" + ("\n".join(f"• {n}" for n in names) if names else "Нет загруженных плагинов.")
        b.button(text="🛒 Магазин плагинов", callback_data="menu:store")
        b.button(text="🔄 Обновить список", callback_data="plugins:reload")
        b.button(text="◀️ Назад", callback_data="menu:main")
        b.adjust(1)
        if is_cb:
            await event.message.edit_text(text, reply_markup=b.as_markup())
            await event.answer()
        else:
            await event.answer(text, reply_markup=b.as_markup())

    @router.callback_query(F.data == "plugins:reload")
    async def plugins_reload(cb: CallbackQuery):
        app.plugins.reload_all()
        await cb.answer("Плагины перезагружены ✅")
        await plugins_menu(cb)

    app.dp.include_router(router)
