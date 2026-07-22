from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

router = Router(name="main_menu")

WELCOME_ART = (
    "⚡〜〜〜〜〜〜〜〜〜〜⚡\n"
    "     🌀 <b>PLAYEROK VORTEX</b> 🌀\n"
    "⚡〜〜〜〜〜〜〜〜〜〜⚡\n"
)

CONTACTS = (
    "📢 Канал: @Vortexplayrock\n"
    "👤 Юз: @Iucdip"
)


def setup(app):
    @router.message(Command("start"))
    async def start_cmd(message: Message):
        if app.is_admin(message.from_user.id):
            await message.answer(
                f"{WELCOME_ART}\n"
                f"Аккаунт: <b>{app.pk_client.account.username}</b>\n"
                f"Инстанс: <code>{app.cfg.instance_name}</code>\n\n"
                f"{CONTACTS}\n\n"
                f"Выбери раздел ниже 👇",
                reply_markup=app.kb.main_menu(),
            )
            return

        if not app.cfg.get("bot.access_password_hash"):
            await message.answer(
                "🌀 Playerok Vortex ещё не полностью настроен: пароль доступа не задан.\n"
                "Запусти бота в интерактивной консоли один раз, чтобы задать пароль ЛК."
            )
            return

        app.pending.set(message.from_user.id, "auth_password")
        await message.answer(
            "🔐 Введи пароль доступа к боту, чтобы стать администратором.\n"
            "Пароль задавался при первом запуске бота в консоли."
        )

    @router.callback_query(F.data == "menu:main")
    async def back_to_main(cb: CallbackQuery):
        await cb.message.edit_text(
            f"{WELCOME_ART}\nВыбери раздел 👇", reply_markup=app.kb.main_menu()
        )
        await cb.answer()

    @router.message(Command("help"))
    async def help_cmd(message: Message):
        await message.answer(
            "🌀 <b>Доступные команды</b>\n\n"
            "/start — главное меню\n"
            "/stats — статистика\n"
            "/deals — последние сделки\n"
            "/blacklist — чёрный список\n"
            "/templates — заготовки ответов\n"
            "/plugins — управление плагинами\n"
            "/reload — перечитать config.yaml",
        )

    @router.message(Command("reload"))
    async def reload_cmd(message: Message):
        if not app.is_admin(message.from_user.id):
            return
        app.cfg.reload()
        await message.answer("♻️ Конфигурация перечитана.")

    app.dp.include_router(router)
