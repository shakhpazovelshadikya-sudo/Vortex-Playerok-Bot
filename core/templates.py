from __future__ import annotations

from core.database import Database


class Templates:
    """Заготовки быстрых ответов (используются из ТГ при ответе в чат Playerok)."""

    def __init__(self, db: Database):
        self.db = db

    def add(self, title: str, text: str) -> int:
        return self.db.execute("INSERT INTO templates(title, text) VALUES(?,?)", (title, text))

    def remove(self, template_id: int):
        self.db.execute("DELETE FROM templates WHERE id=?", (template_id,))

    def all(self):
        return self.db.fetchall("SELECT * FROM templates ORDER BY id")

    def get(self, template_id: int):
        return self.db.fetchone("SELECT * FROM templates WHERE id=?", (template_id,))


class CustomCommands:
    """Команды, которые покупатель может написать в чат Playerok (например '!правила'),
    бот автоматически ответит заранее заданным текстом."""

    def __init__(self, db: Database):
        self.db = db

    def add(self, command: str, response_text: str) -> int:
        command = command.strip().lower()
        return self.db.execute(
            "INSERT INTO custom_commands(command, response_text) VALUES(?,?) "
            "ON CONFLICT(command) DO UPDATE SET response_text=excluded.response_text",
            (command, response_text),
        )

    def remove(self, command: str):
        self.db.execute("DELETE FROM custom_commands WHERE command=?", (command.strip().lower(),))

    def all(self):
        return self.db.fetchall("SELECT * FROM custom_commands ORDER BY id")

    def match(self, message_text: str):
        """Ищет команду, если сообщение покупателя целиком (или начинается с неё) совпадает."""
        if not message_text:
            return None
        text = message_text.strip().lower()
        rows = self.db.fetchall("SELECT * FROM custom_commands WHERE enabled=1")
        for row in rows:
            if text == row["command"] or text.startswith(row["command"] + " "):
                return row
        return None


class AutoResponses:
    """Автоответы на события: новый отзыв, проблема в сделке и т.д."""

    def __init__(self, db: Database):
        self.db = db

    def set(self, trigger_event: str, response_text: str):
        existing = self.db.fetchone(
            "SELECT id FROM auto_responses WHERE trigger_event=?", (trigger_event,)
        )
        if existing:
            self.db.execute(
                "UPDATE auto_responses SET response_text=? WHERE trigger_event=?",
                (response_text, trigger_event),
            )
        else:
            self.db.execute(
                "INSERT INTO auto_responses(trigger_event, response_text) VALUES(?,?)",
                (trigger_event, response_text),
            )

    def get(self, trigger_event: str):
        return self.db.fetchone(
            "SELECT * FROM auto_responses WHERE trigger_event=? AND enabled=1", (trigger_event,)
        )

    def all(self):
        return self.db.fetchall("SELECT * FROM auto_responses ORDER BY id")
