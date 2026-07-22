from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router(name="settings_ui")


def setup(app):
    def _bool_label(key, label):
        val = app.cfg.get(key, False)
        return f"{'✅' if val else '⬜'} {label}"

    @router.callback_query(F.data == "menu:settings")
    async def settings_menu(cb: CallbackQuery):
        b = InlineKeyboardBuilder()
        b.button(text=_bool_label("bot.keep_online", "Вечный онлайн"), callback_data="toggle:bot.keep_online")
        b.button(text=_bool_label("bot.auto_restore_items", "Авто-восстановление"), callback_data="toggle:bot.auto_restore_items")
        b.button(text=_bool_label("bot.auto_confirm_deals", "Авто-подтверждение сделок"), callback_data="toggle:bot.auto_confirm_deals")
        b.button(text=_bool_label("bot.deal_confirm_reminder.enabled", "Напоминания о подтверждении"), callback_data="toggle:bot.deal_confirm_reminder.enabled")
        b.button(text=_bool_label("bot.welcome_message.enabled", "Приветственные сообщения"), callback_data="toggle:bot.welcome_message.enabled")
        b.button(text=_bool_label("bot.autoraise.enabled", "Автоподнятие лотов"), callback_data="toggle:bot.autoraise.enabled")
        b.button(text="✏️ Текст приветствия", callback_data="settings:welcome_text")
        b.button(text="🔔 Уведомления", callback_data="settings:notifications")
        b.button(text="🌐 Прокси Playerok", callback_data="settings:proxy_pk")
        b.button(text="🌐 Прокси Telegram", callback_data="settings:proxy_tg")
        b.button(text="◀️ Назад", callback_data="menu:main")
        b.adjust(1)
        await cb.message.edit_text("🔧 <b>Настройки</b>", reply_markup=b.as_markup())
        await cb.answer()

    @router.callback_query(F.data.startswith("toggle:"))
    async def toggle_flag(cb: CallbackQuery):
        key = cb.data.split(":", 1)[1]
        current = app.cfg.get(key, False)
        app.cfg.set(key, not current)
        app.cfg.save()
        if key.startswith("bot.notifications."):
            await cb.message.edit_reply_markup(reply_markup=app.kb.settings_notifications(app.cfg))
        else:
            await settings_menu(cb)
        await cb.answer("Переключено ✅")

    @router.callback_query(F.data == "settings:notifications")
    async def notif_menu(cb: CallbackQuery):
        await cb.message.edit_text(
            "🔔 <b>Типы уведомлений</b>\nВыбери, о каких событиях получать сообщения:",
            reply_markup=app.kb.settings_notifications(app.cfg),
        )
        await cb.answer()

    @router.callback_query(F.data == "settings:welcome_text")
    async def welcome_text_prompt(cb: CallbackQuery):
        app.pending.set(cb.from_user.id, "set_welcome_text")
        await cb.message.answer("Пришли новый текст приветственного сообщения:")
        await cb.answer()

    @router.callback_query(F.data == "settings:proxy_pk")
    async def proxy_pk_prompt(cb: CallbackQuery):
        app.pending.set(cb.from_user.id, "set_pk_proxy")
        await cb.message.answer(
            "Пришли адрес прокси для Playerok в формате:\n"
            "<code>http://user:pass@host:port</code> или <code>socks5://host:port</code>"
        )
        await cb.answer()

    @router.callback_query(F.data == "settings:proxy_tg")
    async def proxy_tg_prompt(cb: CallbackQuery):
        app.pending.set(cb.from_user.id, "set_tg_proxy")
        await cb.message.answer(
            "Пришли адрес прокси для Telegram в формате:\n"
            "<code>socks5://host:port</code> или <code>http://host:port</code>"
        )
        await cb.answer()

    app.dp.include_router(router)
