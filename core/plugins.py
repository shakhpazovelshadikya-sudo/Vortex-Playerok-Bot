from __future__ import annotations

import importlib.util
import logging
import os
import sys

logger = logging.getLogger("plugins")


class PluginManager:
    """
    Простая система плагинов. Плагин — обычный .py файл в папке plugins/,
    в котором объявлена функция:

        def register(app):
            ...

    Функция register получает объект BotApp и может:
      - подписаться на события через app.on(event_name, callback)
      - добавить свои команды в Telegram через app.dp (aiogram Dispatcher)
      - использовать app.pk_client.account для прямых вызовов Playerok API

    Пример плагина лежит в plugins/example_plugin.py
    """

    def __init__(self, app, plugins_dir: str = "plugins"):
        self.app = app
        self.plugins_dir = plugins_dir
        self.loaded: dict[str, object] = {}

    def load_all(self):
        if not os.path.isdir(self.plugins_dir):
            return
        for fname in sorted(os.listdir(self.plugins_dir)):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            self.load_plugin(fname)

    def load_plugin(self, fname: str):
        path = os.path.join(self.plugins_dir, fname)
        name = fname[:-3]
        try:
            spec = importlib.util.spec_from_file_location(f"plugins.{name}", path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            if hasattr(module, "register"):
                module.register(self.app)
            self.loaded[name] = module
            logger.info("Плагин загружен: %s", name)
        except Exception:
            logger.exception("Не удалось загрузить плагин %s", fname)

    def reload_all(self):
        self.loaded.clear()
        self.load_all()

    def list_names(self) -> list[str]:
        return list(self.loaded.keys())
