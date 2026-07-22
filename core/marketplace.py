from __future__ import annotations

import json
import logging
import os
import time

logger = logging.getLogger("marketplace")


class Marketplace:
    """
    Каталог плагинов, распространяемых через Telegram-канал владельца бота.

    Каталог — обычный JSON-файл (публикуется, например, в канале как
    "закреплённое сообщение со ссылкой на raw-файл" или на любом хостинге),
    формат:

    {
      "channel": "@Vortexplayrock",
      "plugins": [
        {
          "id": "auto_translate",
          "name": "Автоперевод сообщений",
          "description": "Переводит сообщения покупателя на лету",
          "version": "1.0.0",
          "free": true,
          "price": 0,
          "download_url": "https://.../auto_translate.py"
        },
        {
          "id": "premium_stats",
          "name": "Расширенная статистика",
          "description": "Графики, экспорт в Excel, прогноз выручки",
          "version": "1.0.0",
          "free": false,
          "price": 500,
          "currency": "RUB",
          "download_url": "https://.../premium_stats.py",
          "buy_contact": "@Iucdip"
        }
      ]
    }

    Бесплатные плагины ставятся в один клик. Платные — только по
    лицензионному ключу, который покупатель получает у владельца канала.
    """

    def __init__(self, app):
        self.app = app
        self.db = app.db
        self._catalog_cache: list[dict] | None = None
        self._catalog_cached_at: float = 0

    # -------- каталог --------
    def catalog_url(self) -> str:
        return self.app.cfg.get("marketplace.catalog_url", "")

    def fetch_catalog(self, force: bool = False) -> list[dict]:
        if not force and self._catalog_cache is not None and time.time() - self._catalog_cached_at < 300:
            return self._catalog_cache

        url = self.catalog_url()
        if not url:
            self._catalog_cache = []
            return []
        try:
            import requests
            resp = requests.get(url, timeout=10)
            data = resp.json()
            plugins = data.get("plugins", [])
            self._catalog_cache = plugins
            self._catalog_cached_at = time.time()
            self.db.kv_set("marketplace_catalog_cache", plugins)
            return plugins
        except Exception:
            logger.exception("Не удалось загрузить каталог плагинов, использую последний кэш")
            cached = self.db.kv_get("marketplace_catalog_cache", [])
            self._catalog_cache = cached
            return cached

    def find_plugin(self, plugin_id: str) -> dict | None:
        for p in self.fetch_catalog():
            if p.get("id") == plugin_id:
                return p
        return None

    # -------- лицензии --------
    def is_licensed(self, plugin_id: str) -> bool:
        return bool(self.db.fetchone(
            "SELECT 1 FROM plugin_licenses WHERE plugin_id=? AND active=1", (plugin_id,)
        ))

    def save_license(self, plugin_id: str, key: str):
        self.db.execute(
            "INSERT INTO plugin_licenses(plugin_id, license_key, activated_at, active) VALUES(?,?,?,1) "
            "ON CONFLICT(plugin_id) DO UPDATE SET license_key=excluded.license_key, "
            "activated_at=excluded.activated_at, active=1",
            (plugin_id, key, time.time()),
        )

    def is_installed(self, plugin_id: str) -> bool:
        return os.path.exists(os.path.join(self.app.plugins.plugins_dir, f"{plugin_id}.py"))

    # -------- установка --------
    def install_free(self, plugin_id: str) -> tuple[bool, str]:
        plugin = self.find_plugin(plugin_id)
        if not plugin:
            return False, "Плагин не найден в каталоге"
        if not plugin.get("free", False):
            return False, "Этот плагин платный, нужен лицензионный ключ"
        return self._download_and_install(plugin)

    def activate_paid(self, plugin_id: str, license_key: str, user_id: int) -> tuple[bool, str]:
        plugin = self.find_plugin(plugin_id)
        if not plugin:
            return False, "Плагин не найден в каталоге"
        ok, msg = self.app.licensing.verify(plugin_id, license_key, user_id)
        if not ok:
            return False, f"❌ {msg}"
        self.save_license(plugin_id, license_key)
        return self._download_and_install(plugin)

    def _download_and_install(self, plugin: dict) -> tuple[bool, str]:
        url = plugin.get("download_url")
        plugin_id = plugin["id"]
        if not url:
            return False, "У плагина нет ссылки на скачивание"
        try:
            import requests
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            path = os.path.join(self.app.plugins.plugins_dir, f"{plugin_id}.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write(resp.text)
            self.app.plugins.load_plugin(f"{plugin_id}.py")
            return True, f"✅ Плагин «{plugin.get('name', plugin_id)}» установлен."
        except Exception as e:
            logger.exception("Ошибка установки плагина %s", plugin_id)
            return False, f"❌ Ошибка установки: {e}"

    def uninstall(self, plugin_id: str) -> bool:
        path = os.path.join(self.app.plugins.plugins_dir, f"{plugin_id}.py")
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
