"""Служебные скрипты «Города+»: загрузка справочников и наполнение БД.

Запуск модулей:
    python -m scripts.load_cities --help
    python -m scripts.seed_achievements

Общие правила:
- скрипты офлайн, без сетевых вызовов (кроме download_dumps.*);
- настройки берутся из app.config (в т.ч. DATABASE_URL из .env);
- каждый скрипт поддерживает --dry-run, если он ничего не пишет в БД;
- код возврата 0 — успех, 1 — ошибка/несоответствие данных.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "1.0.0"
