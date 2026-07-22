from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


class Keyboards:
    def main_menu(self) -> InlineKeyboardMarkup:
        b = InlineKeyboardBuilder()
        b.button(text="🌀 Сделки", callback_data="menu:deals")
        b.button(text="💬 Чаты", callback_data="menu:chats")
        b.button(text="📦 Автовыдача", callback_data="menu:autodelivery")
        b.button(text="✉️ Заготовки", callback_data="menu:templates")
        b.button(text="⚙️ Автоответы", callback_data="menu:autoresponses")
        b.button(text="🚫 Чёрный список", callback_data="menu:blacklist")
        b.button(text="📊 Статистика", callback_data="menu:stats")
        b.button(text="🔧 Настройки", callback_data="menu:settings")
        b.button(text="🧩 Плагины", callback_data="menu:plugins")
        b.button(text="🛒 Магазин плагинов", callback_data="menu:store")
        b.adjust(2)
        return b.as_markup()

    def deal_actions(self, deal_id: str) -> InlineKeyboardMarkup:
        b = InlineKeyboardBuilder()
        b.button(text="✅ Подтвердить", callback_data=f"deal:confirm:{deal_id}")
        b.button(text="↩️ Вернуть деньги", callback_data=f"deal:refund:{deal_id}")
        b.button(text="📄 Детали", callback_data=f"deal:info:{deal_id}")
        b.button(text="💬 Открыть чат", callback_data=f"deal:chat:{deal_id}")
        b.button(text="✉️ Ответить", callback_data=f"deal:reply:{deal_id}")
        b.adjust(2)
        return b.as_markup()

    def chat_quick_actions(self, chat_id: str) -> InlineKeyboardMarkup:
        b = InlineKeyboardBuilder()
        b.button(text="💬 Открыть чат", callback_data=f"chat:open:{chat_id}")
        b.button(text="✉️ Ответить", callback_data=f"chat:reply:{chat_id}")
        b.button(text="📋 Заготовки", callback_data=f"chat:templates:{chat_id}")
        b.adjust(2)
        return b.as_markup()

    def confirm_cancel(self, action: str, payload: str) -> InlineKeyboardMarkup:
        b = InlineKeyboardBuilder()
        b.button(text="✅ Да", callback_data=f"confirm:{action}:{payload}")
        b.button(text="❌ Отмена", callback_data="confirm:cancel:_")
        b.adjust(2)
        return b.as_markup()

    def templates_list(self, templates: list[dict], target_chat_id: str) -> InlineKeyboardMarkup:
        b = InlineKeyboardBuilder()
        for t in templates:
            b.button(text=t["title"][:32], callback_data=f"tpl:use:{t['id']}:{target_chat_id}")
        b.adjust(1)
        return b.as_markup()

    def back(self, to: str = "menu:main") -> InlineKeyboardMarkup:
        b = InlineKeyboardBuilder()
        b.button(text="◀️ Назад", callback_data=to)
        return b.as_markup()

    def toggle(self, label: str, key: str, value: bool) -> InlineKeyboardButton:
        mark = "✅" if value else "⬜"
        return InlineKeyboardButton(text=f"{mark} {label}", callback_data=f"toggle:{key}")

    def settings_notifications(self, cfg) -> InlineKeyboardMarkup:
        b = InlineKeyboardBuilder()
        keys = [
            ("new_deal", "Новая сделка"),
            ("deal_confirmed", "Подтверждение"),
            ("deal_rolled_back", "Возврат"),
            ("deal_problem", "Проблема"),
            ("deal_problem_resolved", "Проблема решена"),
            ("new_message", "Новое сообщение"),
            ("new_review", "Новый отзыв"),
            ("item_sent", "Товар выдан"),
        ]
        for key, label in keys:
            value = cfg.get(f"bot.notifications.{key}", True)
            b.add(self.toggle(label, f"notifications.{key}", value))
        b.button(text="◀️ Назад", callback_data="menu:settings")
        b.adjust(1)
        return b.as_markup()
