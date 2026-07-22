from __future__ import annotations

import logging
import queue
import threading
import time

from playerokapi.account import Account
from playerokapi.listener.listener import EventListener

logger = logging.getLogger("playerok_client")


class PlayerokClient:
    """
    Обёртка над playerokapi.Account + EventListener.
    Слушатель событий работает в отдельном потоке (т.к. библиотека синхронная),
    и кладёт события в потокобезопасную очередь, которую разбирает асинхронный
    мост событий (core.events_bridge.EventsBridge) в основном event loop бота.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        pk = cfg.get("playerok", {})
        self.account = Account(
            token=pk.get("token"),
            ddg5=pk.get("ddg5", ""),
            cookies=pk.get("cookies") or None,
            proxy=pk.get("proxy") or None,
            requests_timeout=pk.get("requests_timeout", 15),
        )
        self.listener = EventListener(self.account)
        self.event_queue: "queue.Queue" = queue.Queue()

        self._stop_flag = threading.Event()
        self._listener_thread: threading.Thread | None = None
        self._online_thread: threading.Thread | None = None

    # ---------------- lifecycle ----------------
    def init_account(self):
        self.account.get()
        logger.info(
            "Аккаунт Playerok инициализирован: %s (id=%s)",
            self.account.username, self.account.id,
        )
        return self.account

    def start(self):
        self._listener_thread = threading.Thread(
            target=self._listen_loop, name="playerok-listener", daemon=True
        )
        self._listener_thread.start()

        if self.cfg.get("bot.keep_online", True):
            self._online_thread = threading.Thread(
                target=self._keep_online_loop, name="playerok-online", daemon=True
            )
            self._online_thread.start()

    def stop(self):
        self._stop_flag.set()

    # ---------------- internal loops (run in worker threads) ----------------
    def _listen_loop(self):
        while not self._stop_flag.is_set():
            try:
                for event in self.listener.listen():
                    self.event_queue.put(event)
                    if self._stop_flag.is_set():
                        break
            except Exception:
                logger.exception("Слушатель событий упал, перезапуск через 5с")
                time.sleep(5)

    def _keep_online_loop(self):
        interval = self.cfg.get("bot.online_update_interval", 60)
        while not self._stop_flag.is_set():
            try:
                self.account.get()
            except Exception:
                logger.exception("Не удалось обновить онлайн-статус")
            time.sleep(interval)
