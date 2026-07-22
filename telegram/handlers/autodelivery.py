from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router(name="autodelivery")


def setup(app):
    @router.callback_query(F.data == "menu:autodelivery")
    async def list_rules(cb: CallbackQuery):
        rules = app.autodelivery.all()
        b = InlineKeyboardBuilder()
        text_lines = ["📦 <b>Правила автовыдачи</b>\n"]
        if not rules:
            text_lines.append("Пока пусто.")
        for r in rules:
            left = app.autodelivery.goods_left(r["id"])
            kind = f"мульти ({left} шт. осталось)" if left or r["goods_json"] not in (None, "[]", "") else "текст"
            text_lines.append(f"#{r['id']} • «{r['keyword'] or r['item_id']}» • {kind}")
            b.button(text=f"🗑 Удалить #{r['id']}", callback_data=f"ad:del:{r['id']}")
        b.button(text="➕ Добавить правило", callback_data="ad:add")
        b.button(text="◀️ Назад", callback_data="menu:main")
        b.adjust(1)
        await cb.message.edit_text("\n".join(text_lines), reply_markup=b.as_markup())
        await cb.answer()

    @router.callback_query(F.data == "ad:add")
    async def add_rule(cb: CallbackQuery):
        app.pending.set(cb.from_user.id, "ad_keyword")
        await cb.message.answer(
            "Напиши ключевую фразу, при получении которой в чате бот будет автоматически "
            "отправлять товар (например: <code>купить ключ</code>)."
        )
        await cb.answer()

    @router.callback_query(F.data.startswith("ad:del:"))
    async def del_rule(cb: CallbackQuery):
        rule_id = int(cb.data.split(":")[2])
        app.autodelivery.remove_rule(rule_id)
        await cb.answer("Удалено ✅")
        await list_rules(cb)

    app.dp.include_router(router)
