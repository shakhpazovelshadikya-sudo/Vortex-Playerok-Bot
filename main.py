from __future__ import annotations

import asyncio
import logging
import os
import sys

from core.app import BotApp
from core.setup_wizard import ensure_config_ready
from telegram.handlers import setup_all

def _log_name_from_config(config_path: str) -> str:
    base = os.path.splitext(os.path.basename(config_path))[0]
    parent = os.path.basename(os.path.dirname(os.path.abspath(config_path)))
    name = parent if parent and parent != "PlayerokBot" else base
    return f"{name or 'bot'}.log"


_config_path_for_log = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PB_CONFIG", "config.yaml")

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join("logs", _log_name_from_config(_config_path_for_log)), encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("main")


async def main():
    config_path = _config_path_for_log
    ensure_config_ready(config_path)
    app = BotApp(config_path)
    setup_all(app)

    logger.info("🌀 Playerok Vortex запускается (инстанс: %s)...", app.cfg.instance_name)
    await app.start()

    try:
        await app.dp.start_polling(app.bot)
    finally:
        await app.stop()


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🌀 Playerok Vortex остановлен.")
