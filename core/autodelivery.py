from __future__ import annotations

import json
from core.database import Database


class AutoDelivery:
    """
    Правила автовыдачи. Каждое правило привязано либо к ключевой фразе (ищется в тексте
    первого/любого сообщения покупателя), либо к конкретному item_id (тогда выдаётся
    сразу при новой сделке по этому лоту).

    Если задан goods_json (список строк) — это "мульти-выдача": каждому покупателю
    отдаётся следующий свободный уникальный товар из списка, и он больше не будет выдан повторно.
    Если задан response_text — это статичный текст/данные, отправляемые всем одинаково.
    """

    def __init__(self, db: Database):
        self.db = db

    def add_rule(
        self,
        keyword: str = "",
        match_mode: str = "contains",
        item_id: str = "",
        response_text: str = "",
        goods: list[str] | None = None,
    ) -> int:
        return self.db.execute(
            "INSERT INTO autodelivery(keyword, match_mode, item_id, response_text, goods_json, enabled) "
            "VALUES(?,?,?,?,?,1)",
            (keyword, match_mode, item_id, response_text, json.dumps(goods or [], ensure_ascii=False)),
        )

    def remove_rule(self, rule_id: int):
        self.db.execute("DELETE FROM autodelivery WHERE id=?", (rule_id,))

    def all(self):
        return self.db.fetchall("SELECT * FROM autodelivery ORDER BY id")

    def find_for_item(self, item_id: str):
        return self.db.fetchone(
            "SELECT * FROM autodelivery WHERE enabled=1 AND item_id=? AND item_id != ''", (item_id,)
        )

    def find_for_text(self, text: str):
        if not text:
            return None
        text_l = text.lower()
        rows = self.db.fetchall(
            "SELECT * FROM autodelivery WHERE enabled=1 AND keyword != '' AND (item_id='' OR item_id IS NULL)"
        )
        for row in rows:
            kw = (row["keyword"] or "").lower()
            if not kw:
                continue
            if row["match_mode"] == "exact" and text_l.strip() == kw:
                return row
            if row["match_mode"] == "contains" and kw in text_l:
                return row
        return None

    def pop_unique_good(self, rule_id: int) -> str | None:
        """Достаёт из списка товаров следующий свободный уникальный товар (мульти-выдача)."""
        row = self.db.fetchone("SELECT * FROM autodelivery WHERE id=?", (rule_id,))
        if not row:
            return None
        goods = json.loads(row["goods_json"] or "[]")
        if not goods:
            return None
        good = goods.pop(0)
        self.db.execute(
            "UPDATE autodelivery SET goods_json=? WHERE id=?",
            (json.dumps(goods, ensure_ascii=False), rule_id),
        )
        return good

    def goods_left(self, rule_id: int) -> int:
        row = self.db.fetchone("SELECT goods_json FROM autodelivery WHERE id=?", (rule_id,))
        if not row:
            return 0
        return len(json.loads(row["goods_json"] or "[]"))

    def resolve_delivery_text(self, rule: dict) -> str | None:
        """Возвращает текст, который нужно отправить покупателю для данного правила."""
        if rule["goods_json"] and json.loads(rule["goods_json"]):
            good = self.pop_unique_good(rule["id"])
            if good is None:
                return None
            return good
        return rule["response_text"] or None
