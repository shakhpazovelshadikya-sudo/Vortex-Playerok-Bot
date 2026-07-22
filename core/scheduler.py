from __future__ import annotations

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from playerokapi.enums import ItemDealStatuses

logger = logging.getLogger("scheduler")


class BotScheduler:
    def __init__(self, app):
        self.app = app
        self.scheduler = AsyncIOScheduler()

    def start(self):
        raise_cfg = self.app.cfg.get("bot.autoraise", {}) or {}
        if raise_cfg.get("enabled"):
            interval = max(int(raise_cfg.get("interval_minutes", 240)), 5)
            self.scheduler.add_job(
                self._run_autoraise, "interval", minutes=interval, id="autoraise",
                next_run_time=None,
            )
        self.scheduler.start()
        logger.info("Планировщик запущен")

    def stop(self):
        self.scheduler.shutdown(wait=False)

    async def _run_autoraise(self):
        keywords = self.app.cfg.get("bot.autoraise.keywords", []) or []
        await self.app.item_ops.raise_items(keywords or None)

    # ---------------- разовые отложенные задачи ----------------
    def schedule_auto_confirm(self, deal_id: str, delay_seconds: int = 0):
        self.scheduler.add_job(
            self._auto_confirm_job, "date",
            run_date=self._in_seconds(max(delay_seconds, 1)),
            args=[deal_id], id=f"autoconfirm:{deal_id}", replace_existing=True,
        )

    def schedule_confirm_reminder(self, deal):
        cfg = self.app.cfg.get("bot.deal_confirm_reminder", {}) or {}
        delay_min = cfg.get("delay_minutes", 60)
        self.scheduler.add_job(
            self._confirm_reminder_job, "date",
            run_date=self._in_seconds(delay_min * 60),
            args=[deal.id, deal.chat.id if deal.chat else None],
            id=f"reminder:{deal.id}", replace_existing=True,
        )
        repeat_min = cfg.get("repeat_minutes", 0)
        if repeat_min:
            self.scheduler.add_job(
                self._confirm_reminder_job, "interval", minutes=repeat_min,
                start_date=self._in_seconds(delay_min * 60 + repeat_min * 60),
                args=[deal.id, deal.chat.id if deal.chat else None],
                id=f"reminder-repeat:{deal.id}", replace_existing=True,
            )

    def cancel_reminders(self, deal_id: str):
        for job_id in (f"reminder:{deal_id}", f"reminder-repeat:{deal_id}", f"autoconfirm:{deal_id}"):
            try:
                self.scheduler.remove_job(job_id)
            except Exception:
                pass

    def _in_seconds(self, seconds: int):
        import datetime
        return datetime.datetime.now() + datetime.timedelta(seconds=seconds)

    async def _auto_confirm_job(self, deal_id: str):
        app = self.app
        try:
            deal = app.pk_client.account.get_deal(deal_id)
            if deal.status.name in ("SENT",):
                app.pk_client.account.update_deal(deal_id, ItemDealStatuses.CONFIRMED)
                await app.notify_admins(f"✅ Сделка <code>{deal_id}</code> авто-подтверждена по таймеру.")
        except Exception:
            logger.exception("Ошибка авто-подтверждения сделки %s", deal_id)

    async def _confirm_reminder_job(self, deal_id: str, chat_id: str | None):
        app = self.app
        if not chat_id:
            return
        try:
            deal = app.pk_client.account.get_deal(deal_id)
            if deal.status.name != "SENT":
                self.cancel_reminders(deal_id)
                return
            text = app.cfg.get(
                "bot.deal_confirm_reminder.text",
                "Пожалуйста, не забудьте подтвердить получение заказа 🙌",
            )
            await app.send_playerok_message(chat_id, text)
        except Exception:
            logger.exception("Ошибка напоминания о подтверждении сделки %s", deal_id)
