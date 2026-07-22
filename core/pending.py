from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PendingAction:
    action: str
    data: dict = field(default_factory=dict)


class PendingStore:
    """Хранит, чего бот ждёт от конкретного администратора следующим сообщением
    (текст заготовки, ключевое слово автовыдачи, фото для отправки и т.д.)."""

    def __init__(self):
        self._store: dict[int, PendingAction] = {}

    def set(self, user_id: int, action: str, **data):
        self._store[user_id] = PendingAction(action=action, data=data)

    def pop(self, user_id: int) -> PendingAction | None:
        return self._store.pop(user_id, None)

    def get(self, user_id: int) -> PendingAction | None:
        return self._store.get(user_id)

    def clear(self, user_id: int):
        self._store.pop(user_id, None)
