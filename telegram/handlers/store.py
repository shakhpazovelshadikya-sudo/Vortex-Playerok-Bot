from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router(name="store")


def setup(app):
    def _catalog_kb(plugins: list[dict]):
        b = InlineKeyboardBuilder()
        for p in plugins:
            installed = app.marketplace.is_installed(p["id"])
            mark = "✅ " if installed else ("🆓 " if p.get("free") else "💰 ")
            price = "" if p.get("free") else f" — {p.get('price')}{p.get('currency', '₽')}"
            b.button(text=f"{mark}{p['name']}{price}", callback_data=f"store:view:{p['id']}")
        b.button(text="🔄 Обновить каталог", callback_data="store:refresh")
        b.button(text="◀️ Назад", callback_data="menu:plugins")
        b.adjust(1)
        return b.as_markup()

    async def _show_catalog(event, force: bool = False):
        is_cb = isinstance(event, CallbackQuery)
        channel = app.cfg.get("marketplace.channel", "@Vortexplayrock")
        contact = app.cfg.get("marketplace.contact", "@Iucdip")

        if not app.cfg.get("marketplace.catalog_url"):
            text = (
                "🛒 <b>Магазин плагинов</b>\n\n"
                f"Каталог ещё не подключен. Ссылку на актуальный каталог плагинов "
                f"публикует канал {channel}.\n"
                f"Пропиши её в <code>marketplace.catalog_url</code> в config.yaml.\n\n"
                f"По вопросам покупки платных плагинов — {contact}."
            )
            b = InlineKeyboardBuilder()
            b.button(text="◀️ Назад", callback_data="menu:plugins")
            markup = b.as_markup()
        else:
            plugins = app.marketplace.fetch_catalog(force=force)
            if not plugins:
                text = "🛒 Каталог пуст или недоступен. Попробуй «Обновить каталог» позже."
                markup = _catalog_kb([])
            else:
                lines = [
                    "🛒 <b>Магазин плагинов</b>",
                    f"📢 Плагины публикуются в канале {channel}\n",
                ]
                for p in plugins:
                    kind = "🆓 бесплатный" if p.get("free") else f"💰 {p.get('price')}{p.get('currency', '₽')}"
                    lines.append(f"• <b>{p['name']}</b> ({kind}) — {p.get('description', '')}")
                text = "\n".join(lines)
                markup = _catalog_kb(plugins)

        if is_cb:
            await event.message.edit_text(text, reply_markup=markup)
            await event.answer()
        else:
            await event.answer(text, reply_markup=markup)

    @router.message(Command("store"))
    @router.callback_query(F.data == "menu:store")
    async def store_menu(event):
        await _show_catalog(event)

    @router.callback_query(F.data == "store:refresh")
    async def store_refresh(cb: CallbackQuery):
        await _show_catalog(cb, force=True)

    @router.callback_query(F.data.startswith("store:view:"))
    async def store_view(cb: CallbackQuery):
        plugin_id = cb.data.split(":", 2)[2]
        plugin = app.marketplace.find_plugin(plugin_id)
        if not plugin:
            await cb.answer("Плагин не найден", show_alert=True)
            return

        installed = app.marketplace.is_installed(plugin_id)
        b = InlineKeyboardBuilder()
        text = (
            f"🧩 <b>{plugin['name']}</b> (v{plugin.get('version', '?')})\n\n"
            f"{plugin.get('description', '')}\n\n"
        )
        if plugin.get("free"):
            text += "💵 Бесплатный плагин."
            if not installed:
                b.button(text="⬇️ Установить", callback_data=f"store:install_free:{plugin_id}")
        else:
            text += (
                f"💰 Платный: {plugin.get('price')}{plugin.get('currency', '₽')}\n"
                f"По оплате обращайся к {plugin.get('buy_contact', app.cfg.get('marketplace.contact', '@Iucdip'))} "
                f"в канале {app.cfg.get('marketplace.channel', '@Vortexplayrock')}."
            )
            if not installed:
                b.button(text="🔑 Ввести лицензионный ключ", callback_data=f"store:enter_key:{plugin_id}")
        if installed:
            text += "\n\n✅ Уже установлен."
            b.button(text="🗑 Удалить", callback_data=f"store:uninstall:{plugin_id}")
        b.button(text="◀️ Назад", callback_data="menu:store")
        b.adjust(1)
        await cb.message.edit_text(text, reply_markup=b.as_markup())
        await cb.answer()

    @router.callback_query(F.data.startswith("store:install_free:"))
    async def install_free(cb: CallbackQuery):
        plugin_id = cb.data.split(":", 2)[2]
        ok, msg = app.marketplace.install_free(plugin_id)
        await cb.answer(msg if ok else "Ошибка, см. сообщение", show_alert=not ok)
        await cb.message.answer(msg)

    @router.callback_query(F.data.startswith("store:enter_key:"))
    async def enter_key(cb: CallbackQuery):
        plugin_id = cb.data.split(":", 2)[2]
        app.pending.set(cb.from_user.id, "store_license_key", plugin_id=plugin_id)
        await cb.message.answer(
            f"🔑 Пришли лицензионный ключ для плагина <code>{plugin_id}</code>.\n"
            f"Ключ выдаётся после оплаты — обращайся к "
            f"{app.cfg.get('marketplace.contact', '@Iucdip')}."
        )
        await cb.answer()

    @router.callback_query(F.data.startswith("store:uninstall:"))
    async def uninstall(cb: CallbackQuery):
        plugin_id = cb.data.split(":", 2)[2]
        app.marketplace.uninstall(plugin_id)
        await cb.answer("Удалено. Перезапусти бота, чтобы плагин выгрузился из памяти.", show_alert=True)
        await store_view(cb)

    app.dp.include_router(router)
