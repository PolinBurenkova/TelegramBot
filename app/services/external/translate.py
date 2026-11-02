"""Агрегатор провайдеров перевода (каскад ``translate``).

Модуль только реэкспортирует классы уже реализованных провайдеров перевода и
собирает их в ``TRANSLATE_PROVIDERS`` — порядок совпадает с дефолтным каскадом
``app.constants.PROVIDER_CHAINS["translate"]``.

Реализованы и включены: libretranslate, google_translate, deepl,
yandex_translate, mymemory. Пустые (0 байт) модули сюда не импортируются —
иначе был бы ``ImportError``; на момент записи таких среди переводчиков не
осталось.

Ключи: libretranslate — локальный сервис без ключа, остальным нужен свой ключ.
"""
from __future__ import annotations

from app.services.external.base import BaseProvider
from app.services.external.deepl import DeepLProvider
from app.services.external.google_translate import GoogleTranslateProvider
from app.services.external.libretranslate import LibreTranslateProvider
from app.services.external.mymemory import MyMemoryProvider
from app.services.external.yandex_translate import YandexTranslateProvider

TRANSLATE_PROVIDERS: tuple[type[BaseProvider], ...] = (
    LibreTranslateProvider,
    GoogleTranslateProvider,
    DeepLProvider,
    YandexTranslateProvider,
    MyMemoryProvider,
)

__all__ = [
    "TRANSLATE_PROVIDERS",
    "DeepLProvider",
    "GoogleTranslateProvider",
    "LibreTranslateProvider",
    "MyMemoryProvider",
    "YandexTranslateProvider",
]
