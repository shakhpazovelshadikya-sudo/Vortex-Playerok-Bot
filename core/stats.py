from __future__ import annotations

import time
from core.database import Database


class Stats:
    def __init__(self, db: Database):
        self.db = db

    def log(self, event_type: str, deal_id: str = "", amount: float = 0.0):
        self.db.execute(
            "INSERT INTO stats_events(event_type, deal_id, amount, ts) VALUES (?,?,?,?)",
            (event_type, deal_id, amount, time.time()),
        )

    def _since(self, seconds: float) -> float:
        return time.time() - seconds

    def summary(self, period: str = "all") -> dict:
        period_seconds = {
            "day": 86400,
            "week": 86400 * 7,
            "month": 86400 * 30,
            "all": None,
        }.get(period, None)

        where = ""
        params: tuple = ()
        if period_seconds:
            where = "WHERE ts >= ?"
            params = (self._since(period_seconds),)

        deals = self.db.fetchall(
            f"SELECT * FROM stats_events {where} AND event_type='deal_confirmed'"
            if where else "SELECT * FROM stats_events WHERE event_type='deal_confirmed'",
            params,
        )
        refunds = self.db.fetchall(
            f"SELECT * FROM stats_events {where} AND event_type='deal_rolled_back'"
            if where else "SELECT * FROM stats_events WHERE event_type='deal_rolled_back'",
            params,
        )
        new_deals = self.db.fetchall(
            f"SELECT * FROM stats_events {where} AND event_type='new_deal'"
            if where else "SELECT * FROM stats_events WHERE event_type='new_deal'",
            params,
        )

        earned = sum(d["amount"] for d in deals)
        refunded = sum(d["amount"] for d in refunds)

        return {
            "period": period,
            "new_deals": len(new_deals),
            "confirmed_deals": len(deals),
            "refunds": len(refunds),
            "earned": round(earned, 2),
            "refunded": round(refunded, 2),
            "net": round(earned - refunded, 2),
        }

    def format_summary(self, period: str = "all") -> str:
        s = self.summary(period)
        title = {
            "day": "за сегодня",
            "week": "за неделю",
            "month": "за месяц",
            "all": "за всё время",
        }.get(period, period)
        return (
            f"📊 <b>Статистика {title}</b>\n\n"
            f"🆕 Новых сделок: <b>{s['new_deals']}</b>\n"
            f"✅ Подтверждено: <b>{s['confirmed_deals']}</b>\n"
            f"↩️ Возвратов: <b>{s['refunds']}</b>\n"
            f"💰 Заработано: <b>{s['earned']}₽</b>\n"
            f"💸 Возвращено: <b>{s['refunded']}₽</b>\n"
            f"📈 Чистыми: <b>{s['net']}₽</b>"
        )
