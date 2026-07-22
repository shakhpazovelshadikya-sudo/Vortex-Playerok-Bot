from __future__ import annotations

import os
import shutil

import yaml

from core.auth import hash_password

PLACEHOLDER_MARKERS = ("ВАШ_", "your_", "CHANGE_ME", "change-me")

# Только то, без чего бот реально не может стартовать.
# Telegram ID администратора больше НЕ требуется заранее — первый, кто
# напишет боту /start, сам станет админом (см. telegram/handlers/main_menu.py).
REQUIRED_FIELDS = [
    {
        "key": "telegram.token",
        "prompt": "Введите телеграм токен бота (получить у @BotFather)",
        "kind": "str",
    },
    {
        "key": "playerok.token",
        "prompt": (
            "Введите токен с Playerok (значение cookie 'token' с сайта playerok.com).\n"
            "   Проще всего получить через расширение браузера 'Cookie Editor':\n"
            "   зайдите на playerok.com под своим аккаунтом → откройте Cookie Editor →\n"
            "   найдите cookie с именем 'token' → скопируйте её значение"
        ),
        "kind": "str",
    },
]

# Необязательные поля — спрашиваем один раз при самом первом создании конфига,
# и всегда можно пропустить нажатием Enter.
OPTIONAL_FIELDS = [
    {
        "key": "playerok.proxy",
        "prompt": (
            "Введите прокси для Playerok, если он нужен.\n"
            "   Поддерживаемые форматы:\n"
            "     http://host:port\n"
            "     http://логин:пароль@host:port\n"
            "     socks5://host:port\n"
            "     socks5://логин:пароль@host:port\n"
            "   Если прокси не нужен — просто нажмите Enter, чтобы пропустить"
        ),
    },
]


def _is_placeholder(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        if value.strip() == "":
            return True
        return any(marker in value for marker in PLACEHOLDER_MARKERS)
    if isinstance(value, list):
        return len(value) == 0
    return False


def _get_nested(data: dict, dotted_key: str):
    node = data
    for part in dotted_key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _set_nested(data: dict, dotted_key: str, value):
    parts = dotted_key.split(".")
    node = data
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def _ask(prompt_text: str, missing_labels_on_eof: list[str], config_path: str) -> str | None:
    print(f"➡️  {prompt_text}")
    try:
        return input("   > ").strip()
    except EOFError:
        print(
            "\n⚠️  Нет интерактивного терминала (бот запущен в фоне), "
            "поэтому спросить не получится.\n"
            f"Впиши значения вручную в '{config_path}' и перезапусти бота:"
        )
        for label in missing_labels_on_eof:
            print(f"   • {label}")
        raise SystemExit(1)


def _ask_password_setup(data: dict, config_path: str) -> bool:
    """
    Если пароль доступа к боту (ЛК) ещё ни разу не задавался — просит придумать
    его прямо в консоли (дважды, для проверки), сохраняет только хэш+соль.
    В дальнейшем при каждом запуске бота больше не спрашивается.
    """
    if _get_nested(data, "bot.access_password_hash"):
        return False

    print("🔐 Это первый запуск — нужно задать пароль доступа к боту (ЛК).")
    print("   Этот пароль будет спрашиваться у ЛЮБОГО, кто напишет боту /start,")
    print("   прежде чем стать администратором. Спросится только один раз при")
    print("   первом входе — дальше повторно вводить не нужно.\n")

    while True:
        try:
            pwd1 = input("➡️  Придумай пароль: ").strip()
        except EOFError:
            print(
                "\n⚠️  Нет интерактивного терминала — задать пароль сейчас не получится.\n"
                "Запусти бота в интерактивном режиме хотя бы один раз, чтобы задать пароль,\n"
                "либо впиши хэш вручную в bot.access_password_hash / bot.access_password_salt."
            )
            raise SystemExit(1)
        if len(pwd1) < 4:
            print("   ⚠️  Слишком короткий пароль (минимум 4 символа), попробуй ещё раз.")
            continue
        break

    digest, salt = hash_password(pwd1)
    _set_nested(data, "bot.access_password_hash", digest)
    _set_nested(data, "bot.access_password_salt", salt)
    print("   ✅ Пароль сохранён (в открытом виде нигде не хранится).\n")
    return True


def ensure_config_ready(config_path: str, example_path: str = "config.example.yaml") -> None:
    """
    Гарантирует, что перед запуском бота есть рабочий config.yaml:

      1. Если файла нет — создаёт его из config.example.yaml.
      2. Спрашивает по порядку: токен Telegram-бота → прокси Playerok
         (необязательно, только при первом создании конфига) → токен Playerok.
         Если чего-то из этого не хватает — печатает "не смог найти основной
         конфиг :(" и просит ввести именно то, чего не хватает.
      3. При самом первом запуске просит один раз придумать пароль доступа к
         боту (ЛК) — дальше он не запрашивается повторно. Этот пароль будут
         спрашивать у любого, кто напишет боту /start, прежде чем сделать его
         админом — так что Telegram ID заранее вводить не нужно.

    Если всё уже настроено — ничего не спрашивает, бот стартует молча.
    """
    is_fresh = not os.path.exists(config_path)

    if is_fresh:
        if os.path.exists(example_path):
            shutil.copy(example_path, config_path)
        else:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump({}, f)

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    token_field, playerok_field = REQUIRED_FIELDS
    proxy_field = OPTIONAL_FIELDS[0]

    missing_required = [f for f in REQUIRED_FIELDS if _is_placeholder(_get_nested(data, f["key"]))]
    password_missing = not _get_nested(data, "bot.access_password_hash")

    if not missing_required and not password_missing and not is_fresh:
        return  # всё заполнено — тихо продолжаем запуск

    print("\n😕 Не смог найти основной конфиг :(")
    print("Давай быстро настроим его прямо здесь.\n")

    changed = False
    eof_labels = [f["prompt"].splitlines()[0] for f in missing_required]

    # 1) токен телеграм-бота
    if _is_placeholder(_get_nested(data, token_field["key"])):
        while True:
            raw = _ask(token_field["prompt"], eof_labels, config_path)
            if not raw:
                print("   ⚠️  Пустое значение недопустимо, попробуй ещё раз.")
                continue
            _set_nested(data, token_field["key"], raw)
            changed = True
            print("   ✅ Сохранено.\n")
            break

    # 2) прокси для Playerok — необязательно, спрашиваем только при первом создании конфига
    if is_fresh:
        raw = _ask(proxy_field["prompt"], [], config_path)
        if raw:
            _set_nested(data, proxy_field["key"], raw)
            print("   ✅ Прокси сохранён.\n")
        else:
            print("   ⏭  Пропущено (прокси не используется).\n")
        changed = True

    # 3) токен Playerok
    if _is_placeholder(_get_nested(data, playerok_field["key"])):
        while True:
            raw = _ask(playerok_field["prompt"], eof_labels, config_path)
            if not raw:
                print("   ⚠️  Пустое значение недопустимо, попробуй ещё раз.")
                continue
            _set_nested(data, playerok_field["key"], raw)
            changed = True
            print("   ✅ Сохранено.\n")
            break

    # 4) пароль доступа к ЛК — только один раз за всю жизнь конфига
    if _ask_password_setup(data, config_path):
        changed = True

    if changed:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
        print(f"💾 Конфигурация записана в '{config_path}'.\n")

    still_missing = [f for f in REQUIRED_FIELDS if _is_placeholder(_get_nested(data, f["key"]))]
    if still_missing:
        print("⚠️  Бот не сможет полноценно запуститься, пока не заполнены:")
        for f in still_missing:
            print(f"   • {f['key']} — {f['prompt'].splitlines()[0]}")
        print(f"Впиши эти значения в '{config_path}' и запусти бота заново.\n")
        raise SystemExit(1)
