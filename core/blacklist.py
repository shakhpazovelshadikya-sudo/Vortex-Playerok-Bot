from __future__ import annotations

import time
from core.database import Database


class Blacklist:
    def __init__(self, db: Database):
        self.db = db

    def add(self, username: str, reason: str = ""):
        self.db.execute(
            "INSERT INTO blacklist(username, reason, added_at) VALUES(?,?,?) "
            "ON CONFLICT(username) DO UPDATE SET reason=excluded.reason",
            (username.lower(), reason, time.time()),
        )

    def remove(self, username: str):
        self.db.execute("DELETE FROM blacklist WHERE username=?", (username.lower(),))

    def is_blacklisted(self, username: str) -> bool:
        if not username:
            return False
        return bool(self.db.fetchone("SELECT 1 FROM blacklist WHERE username=?", (username.lower(),)))

    def all(self):
        return self.db.fetchall("SELECT * FROM blacklist ORDER BY added_at DESC")
