"""
Пример плагина для Playerok Vortex.

Плагины кладутся в папку plugins/ и подхватываются автоматически при старте
(или по кнопке "Плагины -> Обновить список" в Telegram).

В функцию register(app) передаётся основной объект приложения (BotApp), через
который доступны все сервисы: app.db, app.stats, app.blacklist, app.pk_client,
app.dp (aiogram Dispatcher), app.bot (aiogram Bot) и т.д.
"""

import logging

logger = logging.getLogger("plugin.example")


def register(app):
    # Пример: своя команда в Telegram
    @app.dp.message(lambda m: m.text == "/vortex")
    async def vortex_handler(message):
        await message.answer("🌀 Playerok Vortex одобряет твой магазин!")

    # Пример: подписка на кастомное событие (генерируется вручную из других частей кода)
    def on_new_deal_custom(deal):
        logger.info("Плагин example_plugin увидел новую сделку: %s", deal.id)

    if hasattr(app, "on"):
        app.on("new_deal", on_new_deal_custom)

    logger.info("example_plugin зарегистрирован")
