from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router(name="stats_ui")


def setup(app):
    def _kb():
        b = InlineKeyboardBuilder()
        b.button(text="Сегодня", callback_data="stats:day")
        b.button(text="Месяц", callback_data="stats:month")
        b.button(text="Всё время", callback_data="stats:all")
        b.button(text="◀️ Назад", callback_data="menu:main")
        b.adjust(3, 1)
        return b.as_markup()

    @router.message(Command("stats"))
    @router.callback_query(F.data == "menu:stats")
    async def stats_menu(event):
        is_cb = isinstance(event, CallbackQuery)
        text = app.stats.format_summary("all")
        if is_cb:
            await event.message.edit_text(text, reply_markup=_kb())
            await event.answer()
        else:
            await event.answer(text, reply_markup=_kb())

    @router.callback_query(F.data.startswith("stats:"))
    async def stats_period(cb: CallbackQuery):
        period = cb.data.split(":")[1]
        await cb.message.edit_text(app.stats.format_summary(period), reply_markup=_kb())
        await cb.answer()

    app.dp.include_router(router)
