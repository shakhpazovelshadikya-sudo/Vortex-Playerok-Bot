from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from core.config import Config
from core.database import Database
from core.stats import Stats
from core.blacklist import Blacklist
from core.templates import Templates, CustomCommands, AutoResponses
from core.autodelivery import AutoDelivery
from core.item_ops import ItemOps
from core.playerok_client import PlayerokClient
from core.events_bridge import EventsBridge
from core.scheduler import BotScheduler
from core.plugins import PluginManager
from core.licensing import LicenseManager
from core.marketplace import Marketplace
from core.pending import PendingStore
from telegram.keyboards import Keyboards

logger = logging.getLogger("app")


class BotApp:
    def __init__(self, config_path: str = "config.yaml"):
        self.cfg = Config(config_path)

        self.db = Database(f"data/{self.cfg.instance_name}.db")
        self.stats = Stats(self.db)
        self.blacklist = Blacklist(self.db)
        self.templates = Templates(self.db)
        self.custom_commands = CustomCommands(self.db)
        self.auto_responses = AutoResponses(self.db)
        self.autodelivery = AutoDelivery(self.db)
        self.item_ops = ItemOps(self)
        self.pending = PendingStore()
        self.kb = Keyboards()

        self.pk_client = PlayerokClient(self.cfg)

        tg_proxy = self.cfg.get("telegram.proxy") or None
        session = AiohttpSession(proxy=tg_proxy) if tg_proxy else None
        self.bot = Bot(token=self.cfg.get("telegram.token"), session=session)
        self.dp = Dispatcher()

        self.events_bridge = EventsBridge(self)
        self.scheduler = BotScheduler(self)
        self.plugins = PluginManager(self, "plugins")
        self.licensing = LicenseManager(self)
        self.marketplace = Marketplace(self)

        self._listeners: dict[str, list] = defaultdict(list)

    # -------- простая шина событий для плагинов --------
    def on(self, event_name: str, callback):
        self._listeners[event_name].append(callback)

    def emit(self, event_name: str, *args, **kwargs):
        for cb in self._listeners.get(event_name, []):
            try:
                cb(*args, **kwargs)
            except Exception:
                logger.exception("Ошибка в обработчике плагина для события %s", event_name)

    # -------- админы / уведомления --------
    def is_admin(self, user_id: int) -> bool:
        return user_id in (self.cfg.get("telegram.admins") or [])

    async def notify_admins(self, text: str, kb=None):
        for admin_id in (self.cfg.get("telegram.admins") or []):
            try:
                await self.bot.send_message(admin_id, text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                logger.exception("Не удалось отправить уведомление админу %s", admin_id)

    # -------- обёртки над Playerok API, используемые из мостов/хендлеров --------
    async def send_playerok_message(self, chat_id: str, text: str | None = None, images: list | None = None):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: self.pk_client.account.send_message(chat_id, text, images or [])
        )

    async def restore_item(self, item):
        await self.item_ops.restore_item(item)

    def schedule_auto_confirm(self, deal_id: str, delay_seconds: int = 0):
        self.scheduler.schedule_auto_confirm(deal_id, delay_seconds)

    def schedule_confirm_reminder(self, deal):
        self.scheduler.schedule_confirm_reminder(deal)

    # -------- запуск / остановка --------
    async def start(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.pk_client.init_account)
        self.pk_client.start()

        self.plugins.load_all()
        self.scheduler.start()

        asyncio.create_task(self.events_bridge.run())
        logger.info("BotApp запущен для инстанса '%s'", self.cfg.instance_name)

    async def stop(self):
        self.events_bridge.stop()
        self.scheduler.stop()
        self.pk_client.stop()
        await self.bot.session.close()
