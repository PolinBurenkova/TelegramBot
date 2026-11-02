# app/exceptions.py
"""Иерархия исключений проекта «Города+».

Все прикладные ошибки наследуются от AppError и несут user_message —
текст, который можно показать пользователю в Telegram.
"""

from __future__ import annotations


class AppError(Exception):
    """Базовое исключение приложения."""

    def __init__(self, message: str = "", user_message: str | None = None) -> None:
        final = message or user_message or self.__class__.__name__
        super().__init__(final)
        self.message = final
        self.user_message = user_message or "Что-то пошло не так. Попробуйте позже."


# --- Игровые ошибки ---


class GameError(AppError):
    """Ошибка игровой логики."""


class InvalidCity(GameError):
    """Некорректное название города."""

    def __init__(self, message: str = "", user_message: str | None = None) -> None:
        super().__init__(
            message,
            user_message or "Некорректное название города. Попробуйте ещё раз.",
        )


class CityNotFound(GameError):
    """Город не найден ни в БД, ни у внешних провайдеров."""

    def __init__(self, message: str = "", user_message: str | None = None) -> None:
        super().__init__(
            message or "Город не найден",
            user_message or "Такой город не найден. Попробуйте другой.",
        )


class CityAlreadyUsed(GameError):
    """Город уже назывался в этой игре."""

    def __init__(self, message: str = "", user_message: str | None = None) -> None:
        super().__init__(
            message or "Город уже использован",
            user_message or "Этот город уже назывался. Выберите другой.",
        )


class WrongLetter(GameError):
    """Город начинается не на нужную букву."""

    def __init__(self, message: str = "", user_message: str | None = None) -> None:
        super().__init__(
            message or "Неверная буква",
            user_message or "Город должен начинаться на другую букву.",
        )


class GameNotFound(GameError):
    """Активная игра не найдена."""

    def __init__(self, message: str = "", user_message: str | None = None) -> None:
        super().__init__(
            message or "Игра не найдена",
            user_message or "Активная игра не найдена. Начните новую через /start.",
        )


class ValidationError(AppError):
    """Ошибка валидации пользовательского ввода."""


class RepositoryError(AppError):
    """Сбой операции доступа к данным."""


# --- Ошибки внешних API ---


class ExternalAPIError(AppError):
    """Внешний провайдер вернул ошибку или недоступен."""

    def __init__(
        self,
        message: str = "",
        provider: str | None = None,
        status_code: int | None = None,
        user_message: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, user_message)
        self.provider = provider
        self.status_code = status_code
        self.details = details


class RateLimitError(ExternalAPIError):
    """Превышен rate limit провайдера (обычно HTTP 429)."""


class QuotaExhaustedError(ExternalAPIError):
    """Квота провайдера исчерпана (дневная/месячная)."""


class AllProvidersFailedError(AppError):
    """Все провайдеры в каскаде упали или были пропущены."""

    def __init__(
        self,
        chain_name: str = "",
        attempts: list[dict[str, str]] | None = None,
        *,
        errors: list[Exception] | None = None,
        user_message: str | None = None,
    ) -> None:
        super().__init__(
            f"All providers failed for chain={chain_name!r}",
            user_message or "Сервис временно недоступен, но игра продолжается.",
        )
        self.chain_name = chain_name
        self.attempts = attempts or []
        self.errors = errors or []


class CircuitOpenError(AppError):
    """Circuit breaker открыт — провайдер временно не вызывается."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            f"Circuit breaker is OPEN for provider={provider}",
            user_message="Сервис временно недоступен. Попробуйте позже.",
        )
        self.provider = provider


class ProviderNotConfiguredError(AppError):
    """У провайдера не задан API-ключ."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            f"Provider {provider} is not configured",
            user_message="Сервис временно недоступен.",
        )
        self.provider = provider


class PollingConflictError(RuntimeError):
    """Обновления уже забирает другой экземпляр бота (getUpdates conflict)."""


# Псевдонимы, используемые историческим кодом и check.py
AllProvidersFailed = AllProvidersFailedError
