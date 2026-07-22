#!/usr/bin/env python3
"""
Генератор лицензионных ключей для платных плагинов Playerok Vortex.

Запускать ТОЛЬКО у себя, не отдавать покупателям. Использует тот же секрет,
что прописан в marketplace.license_secret у покупателей в config.yaml —
секрет должен совпадать, иначе ключ не пройдёт проверку.

Использование:
    python3 tools/generate_license.py <plugin_id> [--days 30] [--secret ВАШ_СЕКРЕТ]

Примеры:
    python3 tools/generate_license.py premium_analytics
        -> бессрочный ключ

    python3 tools/generate_license.py premium_analytics --days 30
        -> ключ на 30 дней (для подписочной модели)
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.licensing import LicenseManager


class _FakeCfg:
    def __init__(self, secret):
        self._secret = secret

    def get(self, key, default=None):
        if key == "marketplace.license_secret":
            return self._secret
        return default


class _FakeApp:
    def __init__(self, secret):
        self.cfg = _FakeCfg(secret)


def main():
    parser = argparse.ArgumentParser(description="Генератор лицензионных ключей Playerok Vortex")
    parser.add_argument("plugin_id", help="ID плагина из каталога (напр. premium_analytics)")
    parser.add_argument("--days", type=int, default=None, help="Срок действия в днях (по умолчанию — бессрочно)")
    parser.add_argument(
        "--secret", default=os.environ.get("VORTEX_LICENSE_SECRET", "change-me-secret"),
        help="Секрет для подписи (должен совпадать с marketplace.license_secret в config.yaml покупателя)",
    )
    args = parser.parse_args()

    lm = LicenseManager(_FakeApp(args.secret))
    key = lm.generate_key(args.plugin_id, days=args.days)

    print("\n🌀 Playerok Vortex — лицензионный ключ сгенерирован\n")
    print(f"Плагин:  {args.plugin_id}")
    print(f"Срок:    {'бессрочно' if not args.days else f'{args.days} дней'}")
    print(f"Ключ:    {key}\n")
    print("Отправь этот ключ покупателю. Он вводит его в боте: "
          "🧩 Плагины -> 🛒 Магазин плагинов -> выбрать плагин -> «Ввести лицензионный ключ».")


if __name__ == "__main__":
    main()
