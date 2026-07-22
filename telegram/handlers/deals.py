from __future__ import annotations

import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from playerokapi.enums import ItemDealStatuses

router = Router(name="deals")


def setup(app):
    async def _run(fn, *a, **kw):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*a, **kw))

    @router.message(Command("deals"))
    async def deals_cmd(message: Message):
        if not app.is_admin(message.from_user.id):
            return
        rows = app.db.fetchall("SELECT * FROM deals ORDER BY created_at DESC LIMIT 10")
        if not rows:
            await message.answer("Пока нет сделок.")
            return
        for d in rows:
            await message.answer(
                f"🆔 <code>{d['deal_id']}</code>\n🛒 {d['item_name']}\n👤 {d['buyer_username']}\n"
                f"📌 Статус: <b>{d['status']}</b>\n💵 {d['price']}₽",
                reply_markup=app.kb.deal_actions(d["deal_id"]),
            )

    @router.callback_query(F.data.startswith("deal:confirm:"))
    async def deal_confirm(cb: CallbackQuery):
        deal_id = cb.data.split(":", 2)[2]
        await cb.message.answer(
            "Подтвердить сделку и выплатить продавцу?",
            reply_markup=app.kb.confirm_cancel("deal_confirm", deal_id),
        )
        await cb.answer()

    @router.callback_query(F.data.startswith("deal:refund:"))
    async def deal_refund(cb: CallbackQuery):
        deal_id = cb.data.split(":", 2)[2]
        await cb.message.answer(
            "⚠️ Оформить возврат денег покупателю по этой сделке?",
            reply_markup=app.kb.confirm_cancel("deal_refund", deal_id),
        )
        await cb.answer()

    @router.callback_query(F.data.startswith("confirm:deal_confirm:"))
    async def confirm_deal_confirm(cb: CallbackQuery):
        deal_id = cb.data.split(":", 2)[2]
        try:
            await _run(app.pk_client.account.update_deal, deal_id, ItemDealStatuses.CONFIRMED)
            await cb.message.edit_text(f"✅ Сделка <code>{deal_id}</code> подтверждена.")
        except Exception as e:
            await cb.message.edit_text(f"❌ Ошибка подтверждения: {e}")
        await cb.answer()

    @router.callback_query(F.data.startswith("confirm:deal_refund:"))
    async def confirm_deal_refund(cb: CallbackQuery):
        deal_id = cb.data.split(":", 2)[2]
        try:
            await _run(app.pk_client.account.update_deal, deal_id, ItemDealStatuses.ROLLED_BACK)
            await cb.message.edit_text(f"↩️ Возврат по сделке <code>{deal_id}</code> оформлен.")
        except Exception as e:
            await cb.message.edit_text(f"❌ Ошибка возврата: {e}")
        await cb.answer()

    @router.callback_query(F.data == "confirm:cancel:_")
    async def confirm_cancel(cb: CallbackQuery):
        await cb.message.edit_text("Отменено.")
        await cb.answer()

    @router.callback_query(F.data.startswith("deal:info:"))
    async def deal_info(cb: CallbackQuery):
        deal_id = cb.data.split(":", 2)[2]
        try:
            deal = await _run(app.pk_client.account.get_deal, deal_id)
        except Exception as e:
            await cb.answer(f"Ошибка: {e}", show_alert=True)
            return
        text = (
            f"📄 <b>Детали сделки</b>\n\n"
            f"🆔 <code>{deal.id}</code>\n"
            f"🛒 Товар: {deal.item.name}\n"
            f"💵 Цена: {getattr(deal.item, 'price', '—')}₽\n"
            f"👤 Покупатель: {deal.user.username}\n"
            f"📌 Статус: <b>{deal.status.name}</b>\n"
            f"⚠️ Проблема: {'да' if deal.has_problem else 'нет'}\n"
            f"📅 Создана: {deal.created_at}\n"
            f"💬 Комментарий покупателя: {deal.comment_from_buyer or '—'}"
        )
        await cb.message.answer(text, reply_markup=app.kb.deal_actions(deal.id))
        await cb.answer()

    @router.callback_query(F.data.startswith("deal:chat:"))
    async def deal_chat(cb: CallbackQuery):
        deal_id = cb.data.split(":", 2)[2]
        try:
            deal = await _run(app.pk_client.account.get_deal, deal_id)
        except Exception as e:
            await cb.answer(f"Ошибка: {e}", show_alert=True)
            return
        if not deal.chat:
            await cb.answer("У сделки нет привязанного чата", show_alert=True)
            return
        await _send_chat_history(app, cb.message, deal.chat.id)
        await cb.answer()

    @router.callback_query(F.data.startswith("deal:reply:"))
    async def deal_reply(cb: CallbackQuery):
        deal_id = cb.data.split(":", 2)[2]
        try:
            deal = await _run(app.pk_client.account.get_deal, deal_id)
        except Exception as e:
            await cb.answer(f"Ошибка: {e}", show_alert=True)
            return
        if not deal.chat:
            await cb.answer("У сделки нет привязанного чата", show_alert=True)
            return
        app.pending.set(cb.from_user.id, "reply_to_chat", chat_id=deal.chat.id)
        await cb.message.answer(
            f"✍️ Напиши текст, который отправить покупателю в чат по сделке <code>{deal_id}</code>.\n"
            f"Можно также прислать фото/GIF — они уйдут вложением.\n"
            f"Отправь /cancel для отмены."
        )
        await cb.answer()

    app.dp.include_router(router)


async def _send_chat_history(app, message: Message, chat_id: str, count: int = 15):
    loop = None
    import asyncio as _a
    loop = _a.get_running_loop()
    msgs = await loop.run_in_executor(
        None, lambda: app.pk_client.account.get_chat_messages(chat_id, count=count)
    )
    lines = [f"💬 <b>История чата</b> <code>{chat_id}</code>\n"]
    for m in reversed(msgs.messages):
        who = "🧑 Покупатель" if (m.user and m.user.username != app.pk_client.account.username) else "🌀 Вы"
        text_ = getattr(m, "text", "") or "[вложение]"
        lines.append(f"{who}: {text_}")
    text_block = "\n".join(lines)[-3900:]
    await message.answer(text_block, reply_markup=app.kb.chat_quick_actions(chat_id))
