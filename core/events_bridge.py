from __future__ import annotations

import asyncio
import logging

from playerokapi.enums import ItemDealStatuses
from playerokapi.listener import events as ev

logger = logging.getLogger("events_bridge")


def _username(user_profile) -> str:
    try:
        return user_profile.username or user_profile.id
    except Exception:
        return "unknown"


class EventsBridge:
    """
    Забирает события из очереди PlayerokClient и раздаёт их всем подсистемам:
    уведомления в TG, автовыдача, автовосстановление, автоподтверждение,
    напоминания, приветствия, автоответы, кастомные команды, статистика, ЧС.
    """

    def __init__(self, app):
        self.app = app  # ссылка на объект BotApp (см. main.py) со всеми сервисами
        self._running = False

    async def run(self):
        self._running = True
        client = self.app.pk_client
        loop = asyncio.get_running_loop()
        while self._running:
            try:
                event = await loop.run_in_executor(None, client.event_queue.get, True, 1.0)
            except Exception:
                await asyncio.sleep(0.2)
                continue
            if event is None:
                continue
            try:
                await self.handle_event(event)
            except Exception:
                logger.exception("Ошибка обработки события %r", type(event))

    def stop(self):
        self._running = False

    # ------------------------------------------------------------------
    async def handle_event(self, event):
        app = self.app

        if isinstance(event, ev.NewMessageEvent):
            await self._on_new_message(event)

        elif isinstance(event, ev.NewDealEvent):
            await self._on_new_deal(event)

        elif isinstance(event, ev.ItemPaidEvent):
            await self._on_item_paid(event)

        elif isinstance(event, ev.ItemSentEvent):
            await self._on_item_sent(event)

        elif isinstance(event, ev.DealConfirmedEvent):
            await self._on_deal_confirmed(event)

        elif isinstance(event, ev.DealRolledBackEvent):
            await self._on_deal_rolled_back(event)

        elif isinstance(event, ev.DealHasProblemEvent):
            await self._on_deal_problem(event)

        elif isinstance(event, ev.DealProblemResolvedEvent):
            await self._on_deal_problem_resolved(event)

        elif isinstance(event, ev.NewReviewEvent):
            await self._on_new_review(event)

        elif isinstance(event, ev.ChatInitializedEvent):
            pass  # можно логировать при желании

    # ------------------------------------------------------------------
    async def _notify(self, key: str, text: str, kb=None):
        if not self.app.cfg.get(f"bot.notifications.{key}", True):
            return
        await self.app.notify_admins(text, kb=kb)

    async def _on_new_message(self, event: ev.NewMessageEvent):
        app = self.app
        msg = event.message
        chat = event.chat
        text = getattr(msg, "text", "") or ""

        # игнорируем свои же сообщения
        try:
            if getattr(msg, "user", None) and _username(msg.user) == app.pk_client.account.username:
                return
        except Exception:
            pass

        buyer = None
        try:
            buyer = _username(msg.user)
        except Exception:
            pass

        # чёрный список
        if buyer and app.blacklist.is_blacklisted(buyer):
            return

        # кастомные команды покупателя
        cmd_row = app.custom_commands.match(text)
        if cmd_row:
            await app.send_playerok_message(chat.id, cmd_row["response_text"])

        # автовыдача по ключевой фразе (если это не команда)
        elif app.cfg.get("bot.autodelivery_by_message", True):
            rule = app.autodelivery.find_for_text(text)
            if rule:
                delivery_text = app.autodelivery.resolve_delivery_text(rule)
                if delivery_text:
                    await app.send_playerok_message(chat.id, delivery_text)
                else:
                    await app.notify_admins(
                        f"⚠️ Закончились уникальные товары для автовыдачи по правилу #{rule['id']} "
                        f"(ключ: <code>{rule['keyword']}</code>)"
                    )

        if app.cfg.get("bot.notifications.new_message", True):
            preview = text[:300] if text else "[изображение/файл]"
            await app.notify_admins(
                f"💬 <b>Новое сообщение</b>\n👤 От: <code>{buyer}</code>\n\n{preview}",
                kb=app.kb.chat_quick_actions(chat.id),
            )

    async def _on_new_deal(self, event: ev.NewDealEvent):
        app = self.app
        deal = event.deal
        buyer = _username(deal.user)

        if buyer and app.blacklist.is_blacklisted(buyer):
            logger.info("Сделка от пользователя из ЧС (%s), уведомление подавлено", buyer)

        app.db.execute(
            "INSERT INTO deals(deal_id, item_id, item_name, buyer_username, chat_id, status, price, created_at) "
            "VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(deal_id) DO UPDATE SET status=excluded.status",
            (
                deal.id, deal.item.id, deal.item.name, buyer,
                deal.chat.id if deal.chat else "", deal.status.name,
                float(getattr(deal.item, "price", 0) or 0), event.time,
            ),
        )
        app.stats.log("new_deal", deal.id, float(getattr(deal.item, "price", 0) or 0))

        # приветственное сообщение
        if app.cfg.get("bot.welcome_message.enabled", False) and deal.chat:
            welcome_text = app.cfg.get("bot.welcome_message.text", "")
            if welcome_text:
                await app.send_playerok_message(deal.chat.id, welcome_text)

        # автовыдача, привязанная к конкретному лоту (выдаём сразу, без ожидания оплаты)
        rule = app.autodelivery.find_for_item(deal.item.id)
        if rule and deal.chat:
            delivery_text = app.autodelivery.resolve_delivery_text(rule)
            if delivery_text:
                await app.send_playerok_message(deal.chat.id, delivery_text)
                app.db.execute("UPDATE deals SET delivered=1 WHERE deal_id=?", (deal.id,))

        await self._notify(
            "new_deal",
            f"🆕 <b>Новая сделка</b>\n"
            f"🛒 Товар: <b>{deal.item.name}</b>\n"
            f"💵 Цена: <b>{getattr(deal.item, 'price', '—')}₽</b>\n"
            f"👤 Покупатель: <code>{buyer}</code>\n"
            f"🆔 ID сделки: <code>{deal.id}</code>",
            kb=app.kb.deal_actions(deal.id),
        )

    async def _on_item_paid(self, event: ev.ItemPaidEvent):
        app = self.app
        deal = event.deal
        # автовосстановление товара — переставляем такой же лот, чтобы позиция снова была в продаже
        if app.cfg.get("bot.auto_restore_items", True):
            await app.restore_item(deal.item)

    async def _on_item_sent(self, event: ev.ItemSentEvent):
        app = self.app
        deal = event.deal
        app.db.execute("UPDATE deals SET status=? WHERE deal_id=?", (deal.status.name, deal.id))

        if app.cfg.get("bot.auto_confirm_deals", False):
            delay = app.cfg.get("bot.auto_confirm_delay", 0)
            app.schedule_auto_confirm(deal.id, delay)

        if app.cfg.get("bot.deal_confirm_reminder.enabled", True):
            app.schedule_confirm_reminder(deal)

    async def _on_deal_confirmed(self, event: ev.DealConfirmedEvent):
        app = self.app
        deal = event.deal
        price = float(getattr(deal.item, "price", 0) or 0)
        app.db.execute(
            "UPDATE deals SET status=?, confirmed_at=? WHERE deal_id=?",
            (deal.status.name, event.time, deal.id),
        )
        app.stats.log("deal_confirmed", deal.id, price)

        resp = app.auto_responses.get("deal_confirmed")
        if resp and deal.chat:
            await app.send_playerok_message(deal.chat.id, resp["response_text"])

        await self._notify(
            "deal_confirmed",
            f"✅ <b>Сделка подтверждена</b>\n🛒 {deal.item.name}\n💵 +{price}₽\n🆔 <code>{deal.id}</code>",
        )

    async def _on_deal_rolled_back(self, event: ev.DealRolledBackEvent):
        app = self.app
        deal = event.deal
        price = float(getattr(deal.item, "price", 0) or 0)
        app.db.execute(
            "UPDATE deals SET status=?, rolled_back_at=? WHERE deal_id=?",
            (deal.status.name, event.time, deal.id),
        )
        app.stats.log("deal_rolled_back", deal.id, price)

        await self._notify(
            "deal_rolled_back",
            f"↩️ <b>Сделка возвращена</b>\n🛒 {deal.item.name}\n💵 -{price}₽\n🆔 <code>{deal.id}</code>",
        )

    async def _on_deal_problem(self, event: ev.DealHasProblemEvent):
        app = self.app
        deal = event.deal

        resp = app.auto_responses.get("deal_problem")
        if resp and deal.chat:
            await app.send_playerok_message(deal.chat.id, resp["response_text"])

        await self._notify(
            "deal_problem",
            f"⚠️ <b>Проблема в сделке!</b>\n🛒 {deal.item.name}\n👤 {_username(deal.user)}\n🆔 <code>{deal.id}</code>\n\n"
            f"{deal.status_description or ''}",
            kb=app.kb.deal_actions(deal.id),
        )

    async def _on_deal_problem_resolved(self, event: ev.DealProblemResolvedEvent):
        app = self.app
        deal = event.deal
        await self._notify(
            "deal_problem_resolved",
            f"🛠 <b>Проблема в сделке решена</b>\n🛒 {deal.item.name}\n🆔 <code>{deal.id}</code>",
        )

    async def _on_new_review(self, event: ev.NewReviewEvent):
        app = self.app
        deal = event.deal

        resp = app.auto_responses.get("new_review")
        if resp and deal.chat:
            await app.send_playerok_message(deal.chat.id, resp["response_text"])

        stars = getattr(deal.review, "rating", None) if getattr(deal, "review", None) else None
        text_ = getattr(deal.review, "text", "") if getattr(deal, "review", None) else ""
        await self._notify(
            "new_review",
            f"⭐ <b>Новый отзыв</b> ({stars if stars is not None else '—'}/5)\n"
            f"🛒 {deal.item.name}\n👤 {_username(deal.user)}\n\n{text_ or '(без текста)'}",
        )
