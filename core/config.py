from __future__ import annotations

import os
import copy
import yaml

DEFAULT_CONFIG_PATH = os.environ.get("PB_CONFIG", "config.yaml")


class Config:
    """Обёртка над YAML-конфигом с доступом по точке и hot-reload."""

    def __init__(self, path: str = DEFAULT_CONFIG_PATH):
        self.path = path
        self._data: dict = {}
        self.load()

    def load(self):
        if not os.path.exists(self.path):
            raise FileNotFoundError(
                f"Файл конфигурации '{self.path}' не найден. "
                f"Скопируйте config.example.yaml -> config.yaml и заполните его."
            )
        with open(self.path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f) or {}

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self._data, f, allow_unicode=True, sort_keys=False)

    def reload(self):
        self.load()

    def get(self, dotted_key: str, default=None):
        node = self._data
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, dotted_key: str, value):
        parts = dotted_key.split(".")
        node = self._data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    def as_dict(self) -> dict:
        return copy.deepcopy(self._data)

    # удобные шорткаты
    @property
    def instance_name(self) -> str:
        return self.get("bot.instance_name", "default")
