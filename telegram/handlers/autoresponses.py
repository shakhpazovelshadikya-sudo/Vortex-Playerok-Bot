from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router(name="autoresponses")

EVENTS = [
    ("new_review", "⭐ Новый отзыв"),
    ("deal_problem", "⚠️ Проблема в сделке"),
    ("deal_confirmed", "✅ Сделка подтверждена"),
]


def setup(app):
    @router.callback_query(F.data == "menu:autoresponses")
    async def list_ar(cb: CallbackQuery):
        b = InlineKeyboardBuilder()
        lines = ["⚙️ <b>Автоответы на события</b>\n"]
        for key, label in EVENTS:
            row = app.auto_responses.get(key)
            status = "✅ настроен" if row else "— не настроен"
            lines.append(f"{label}: {status}")
            b.button(text=f"✏️ {label}", callback_data=f"ar:set:{key}")
        b.button(text="◀️ Назад", callback_data="menu:main")
        b.adjust(1)
        await cb.message.edit_text("\n".join(lines), reply_markup=b.as_markup())
        await cb.answer()

    @router.callback_query(F.data.startswith("ar:set:"))
    async def set_ar(cb: CallbackQuery):
        event_key = cb.data.split(":", 2)[2]
        app.pending.set(cb.from_user.id, "add_autoresponse_text", trigger_event=event_key)
        await cb.message.answer("Пришли текст автоответа для этого события:")
        await cb.answer()

    app.dp.include_router(router)
