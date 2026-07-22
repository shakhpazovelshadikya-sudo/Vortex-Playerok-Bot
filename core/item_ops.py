from __future__ import annotations

import logging

logger = logging.getLogger("item_ops")


class ItemOps:
    """Операции над лотами: авто-восстановление после продажи, авто-поднятие в топ."""

    def __init__(self, app):
        self.app = app

    async def restore_item(self, sold_item):
        """
        После продажи товар в Playerok становится недоступен для повторной покупки.
        Чтобы "вечно" держать позицию в продаже (для товаров с несколькими копиями),
        создаём новый предмет-клон с теми же параметрами и публикуем его.
        """
        app = self.app
        account = app.pk_client.account
        try:
            full_item = account.get_item(sold_item.id)
        except Exception:
            full_item = sold_item

        try:
            new_item = account.create_item(
                game_category_id=full_item.game_category.id if getattr(full_item, "game_category", None) else full_item.game_category_id,
                obtaining_type_id=full_item.obtaining_type.id if getattr(full_item, "obtaining_type", None) else full_item.obtaining_type_id,
                name=full_item.name,
                price=full_item.price,
                description=full_item.description or "",
                options=getattr(full_item, "options", []) or [],
                data_fields=getattr(full_item, "data_fields", []) or [],
                attachments=[],
            )
            statuses = account.get_item_priority_statuses(new_item.id, full_item.price)
            default_status = statuses[0] if statuses else None
            if default_status:
                account.publish_item(new_item.id, default_status.id)
            logger.info("Товар восстановлен: %s -> новый ID %s", sold_item.id, new_item.id)
            await app.notify_admins(
                f"♻️ Товар <b>{full_item.name}</b> авто-восстановлен и снова в продаже."
            )
        except Exception:
            logger.exception("Не удалось авто-восстановить товар %s", getattr(sold_item, "id", "?"))
            await app.notify_admins(
                f"⚠️ Не удалось авто-восстановить товар <b>{getattr(sold_item, 'name', '?')}</b>. "
                f"Проверьте логи."
            )

    async def raise_items(self, keywords: list[str] | None = None):
        """Поднимает лоты пользователя в топ (по возможности, если статус бесплатный/доступен)."""
        app = self.app
        account = app.pk_client.account
        try:
            items = account.get_my_items()
        except Exception:
            logger.exception("Не удалось получить список лотов для автоподнятия")
            return

        raised = 0
        for it in getattr(items, "items", items if isinstance(items, list) else []):
            if keywords and not any(k.lower() in (it.name or "").lower() for k in keywords):
                continue
            try:
                statuses = account.get_item_priority_statuses(it.id, it.price)
                free_status = next((s for s in statuses if getattr(s, "price", 0) in (0, None)), None)
                if free_status:
                    account.increase_item_priority_status(it.id, free_status.id)
                    raised += 1
            except Exception:
                logger.exception("Ошибка автоподнятия лота %s", it.id)

        if raised:
            await app.notify_admins(f"⬆️ Автоподнятие: поднято лотов — {raised}")
