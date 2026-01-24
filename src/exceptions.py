"""Пользовательские исключения для product-service."""

from typing import Any


class AppException(Exception):
    """Базовое исключение приложения."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundException(AppException):
    """Ресурс не найден (404)."""

    pass


class BadRequestException(AppException):
    """Неверный запрос (400)."""

    pass


class ConflictException(AppException):
    """Конфликт данных (409)."""

    pass


class ValidationException(AppException):
    """Ошибка валидации (422)."""

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.errors = errors or []
