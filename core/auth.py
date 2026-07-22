from __future__ import annotations

import hashlib
import hmac
import os


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Возвращает (hash_hex, salt_hex). Соль генерируется, если не передана."""
    if salt is None:
        salt = os.urandom(16).hex()
    salt_bytes = bytes.fromhex(salt)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 200_000)
    return digest.hex(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    if not stored_hash or not salt:
        return False
    try:
        digest, _ = hash_password(password, salt)
    except Exception:
        return False
    return hmac.compare_digest(digest, stored_hash)
