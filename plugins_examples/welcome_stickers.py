"""
Пример БЕСПЛАТНОГО плагина маркетплейса — «Приветственные стикеры».

Это демонстрация того, как должен выглядеть .py файл плагина, который
владелец канала @Vortexplayrock выкладывает по ссылке download_url в
каталоге (plugins_catalog.example.json). Пользователи ставят такие плагины
в один клик через 🛒 Магазин плагинов -> плагин бесплатный -> Установить.

Структура ничем не отличается от обычных локальных плагинов — единственная
разница в том, ЧТО этот файл лежит не в plugins/ у пользователя изначально,
а скачивается ботом из твоего канала/хостинга при установке.
"""

import random
import logging

logger = logging.getLogger("plugin.welcome_stickers")

STICKERS = [
    "CAACAgIAAxkBAAEBWelcome1",  # замените на реальные file_id стикеров
    "CAACAgIAAxkBAAEBWelcome2",
]


def register(app):
    original_bridge_on_new_deal = None

    def send_sticker_on_new_deal(deal_obj):
        # Пример подписки на внутреннее событие бота (эмиттится вручную,
        # если вы вызываете app.emit("new_deal", deal) в своём коде).
        logger.info("welcome_stickers: новая сделка %s — отправляю стикер", getattr(deal_obj, "id", "?"))

    app.on("new_deal", send_sticker_on_new_deal)
    logger.info("Плагин welcome_stickers зарегистрирован")
