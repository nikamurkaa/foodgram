"""Обработчики исключений REST API проекта."""

from rest_framework.views import exception_handler


def foodgram_exception_handler(exc, context):
    """Преобразует исключение API в стандартный ответ DRF."""

    return exception_handler(exc, context)
