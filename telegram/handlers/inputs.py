from __future__ import annotations

import json
from aiogram import Router, F
from aiogram.types import Message

from core.auth import verify_password

router = Router(name="inputs")


def setup(app):
    @router.message(F.photo | F.animation | F.document)
    async def media_input(message: Message):
        pending = app.pending.get(message.from_user.id)
        if not pending or pending.action != "reply_to_chat":
            return
        chat_id = pending.data["chat_id"]
        file_id = None
        if message.photo:
            file_id = message.photo[-1].file_id
        elif message.animation:
            file_id = message.animation.file_id
        elif message.document:
            file_id = message.document.file_id
        if not file_id:
            return
        file = await app.bot.get_file(file_id)
        buf = await app.bot.download_file(file.file_path)
        caption = message.caption or ""
        await app.send_playerok_message(chat_id, caption, images=[buf.read()])
        app.pending.clear(message.from_user.id)
        await message.answer("✅ Отправлено в чат Playerok.")

    @router.message(F.text)
    async def text_input(message: Message):
        pending = app.pending.get(message.from_user.id)

        # Проверка пароля доступа к ЛК — единственное действие, доступное НЕ-админам
        if pending and pending.action == "auth_password":
            app.pending.clear(message.from_user.id)
            stored_hash = app.cfg.get("bot.access_password_hash")
            stored_salt = app.cfg.get("bot.access_password_salt")
            if verify_password(message.text.strip(), stored_hash, stored_salt):
                admins = list(app.cfg.get("telegram.admins") or [])
                if message.from_user.id not in admins:
                    admins.append(message.from_user.id)
                    app.cfg.set("telegram.admins", admins)
                    app.cfg.save()
                await message.answer(
                    "✅ Пароль верный. Ты теперь администратор бота — присылай /start ещё раз, "
                    "чтобы открыть меню."
                )
            else:
                await message.answer("❌ Неверный пароль.")
            return

        if not app.is_admin(message.from_user.id):
            return
        if not pending:
            return  # обычное сообщение без контекста — игнорируем

        action = pending.action
        data = pending.data

        if action == "reply_to_chat":
            await app.send_playerok_message(data["chat_id"], message.text)
            app.pending.clear(message.from_user.id)
            await message.answer("✅ Отправлено в чат Playerok.")

        elif action == "add_template_title":
            app.pending.set(message.from_user.id, "add_template_text", title=message.text)
            await message.answer("Теперь пришли текст заготовки:")

        elif action == "add_template_text":
            app.templates.add(data["title"], message.text)
            app.pending.clear(message.from_user.id)
            await message.answer(f"✅ Заготовка «{data['title']}» сохранена.")

        elif action == "add_blacklist_user":
            uname = message.text.strip().lstrip("@")
            app.blacklist.add(uname, reason="добавлен вручную из ТГ")
            app.pending.clear(message.from_user.id)
            await message.answer(f"🚫 Пользователь @{uname} добавлен в чёрный список.")

        elif action == "remove_blacklist_user":
            uname = message.text.strip().lstrip("@")
            app.blacklist.remove(uname)
            app.pending.clear(message.from_user.id)
            await message.answer(f"✅ @{uname} удалён из чёрного списка.")

        elif action == "add_command_name":
            app.pending.set(message.from_user.id, "add_command_text", command=message.text.strip().lower())
            await message.answer("Теперь пришли текст ответа на эту команду:")

        elif action == "add_command_text":
            app.custom_commands.add(data["command"], message.text)
            app.pending.clear(message.from_user.id)
            await message.answer(f"✅ Команда «{data['command']}» сохранена.")

        elif action == "add_autoresponse_text":
            app.auto_responses.set(data["trigger_event"], message.text)
            app.pending.clear(message.from_user.id)
            await message.answer(f"✅ Автоответ для события «{data['trigger_event']}» сохранён.")

        elif action == "ad_keyword":
            app.pending.set(message.from_user.id, "ad_text", keyword=message.text.strip())
            await message.answer(
                "Теперь пришли текст, который отправлять при этой ключевой фразе.\n"
                "Если хочешь мульти-выдачу уникальных товаров — пришли их через /goods, "
                "каждый товар с новой строки, вместо обычного текста."
            )

        elif action == "ad_text":
            text = message.text
            if text.strip().startswith("/goods"):
                goods = [g for g in text.split("\n")[1:] if g.strip()]
                app.autodelivery.add_rule(keyword=data["keyword"], goods=goods)
                await message.answer(f"✅ Мульти-выдача добавлена: {len(goods)} уникальных товаров.")
            else:
                app.autodelivery.add_rule(keyword=data["keyword"], response_text=text)
                await message.answer("✅ Правило автовыдачи добавлено.")
            app.pending.clear(message.from_user.id)

        elif action == "set_pk_proxy":
            app.cfg.set("playerok.proxy", message.text.strip())
            app.cfg.save()
            app.pending.clear(message.from_user.id)
            await message.answer("✅ Прокси Playerok сохранён. Перезапустите бота, чтобы применить.")

        elif action == "set_tg_proxy":
            app.cfg.set("telegram.proxy", message.text.strip())
            app.cfg.save()
            app.pending.clear(message.from_user.id)
            await message.answer("✅ Прокси Telegram сохранён. Перезапустите бота, чтобы применить.")

        elif action == "store_license_key":
            plugin_id = data["plugin_id"]
            ok, msg = app.marketplace.activate_paid(plugin_id, message.text.strip(), message.from_user.id)
            app.pending.clear(message.from_user.id)
            await message.answer(msg)

        elif action == "set_welcome_text":
            app.cfg.set("bot.welcome_message.text", message.text)
            app.cfg.set("bot.welcome_message.enabled", True)
            app.cfg.save()
            app.pending.clear(message.from_user.id)
            await message.answer("✅ Приветственное сообщение сохранено и включено.")

    app.dp.include_router(router)
