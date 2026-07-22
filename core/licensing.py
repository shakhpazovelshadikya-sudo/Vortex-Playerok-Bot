from __future__ import annotations

import base64
import hashlib
import hmac
import time
import logging

logger = logging.getLogger("licensing")


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


class LicenseManager:
    """
    Лёгкая система лицензионных ключей для платных плагинов.

    Формат ключа:  <plugin_id>.<expires_ts или 0>.<подпись>
    Подпись = HMAC-SHA256(secret, "<plugin_id>.<expires_ts>") в base64url.

    ВАЖНО (честно предупреждаем): секрет (marketplace.license_secret) хранится
    в config.yaml у КАЖДОГО покупателя бота. Это простая защита "от ленивого
    подбора", а не крипто-стойкий DRM — технически владелец секрета мог бы
    сам подписать себе ключ. Если нужна более строгая защита — используйте
    marketplace.license_check_url (см. ниже), тогда ключи проверяются на
    твоём сервере, а секрет никуда не публикуется.
    """

    def __init__(self, app):
        self.app = app

    @property
    def secret(self) -> str:
        return self.app.cfg.get("marketplace.license_secret", "") or "change-me-secret"

    # ---------------- генерация (используется владельцем каталога) ----------------
    def generate_key(self, plugin_id: str, days: int | None = None) -> str:
        expires = int(time.time() + days * 86400) if days else 0
        payload = f"{plugin_id}.{expires}"
        sig = hmac.new(self.secret.encode(), payload.encode(), hashlib.sha256).digest()
        return f"{payload}.{_b64u(sig)}"

    # ---------------- проверка (используется ботом покупателя) ----------------
    def verify_key_offline(self, plugin_id: str, key: str) -> tuple[bool, str]:
        try:
            parts = key.strip().split(".")
            if len(parts) != 3:
                return False, "Неверный формат ключа"
            key_plugin_id, expires_str, sig_b64 = parts
            if key_plugin_id != plugin_id:
                return False, "Ключ выдан для другого плагина"
            payload = f"{key_plugin_id}.{expires_str}"
            expected_sig = hmac.new(self.secret.encode(), payload.encode(), hashlib.sha256).digest()
            if not hmac.compare_digest(_b64u(expected_sig), sig_b64):
                return False, "Неверная подпись ключа"
            expires = int(expires_str)
            if expires and time.time() > expires:
                return False, "Срок действия ключа истёк"
            return True, "OK"
        except Exception:
            logger.exception("Ошибка проверки лицензионного ключа")
            return False, "Ошибка проверки ключа"

    def verify_key_remote(self, plugin_id: str, key: str, user_id: int) -> tuple[bool, str]:
        url = self.app.cfg.get("marketplace.license_check_url", "")
        if not url:
            return self.verify_key_offline(plugin_id, key)
        try:
            import requests
            resp = requests.post(
                url, json={"plugin_id": plugin_id, "key": key, "telegram_user_id": user_id}, timeout=10
            )
            data = resp.json()
            return bool(data.get("valid")), data.get("message", "OK" if data.get("valid") else "Ключ недействителен")
        except Exception:
            logger.exception("Ошибка удалённой проверки ключа, фолбэк на офлайн-проверку")
            return self.verify_key_offline(plugin_id, key)

    def verify(self, plugin_id: str, key: str, user_id: int = 0) -> tuple[bool, str]:
        if self.app.cfg.get("marketplace.license_check_url", ""):
            return self.verify_key_remote(plugin_id, key, user_id)
        return self.verify_key_offline(plugin_id, key)
