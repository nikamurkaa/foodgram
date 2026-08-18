"""Конфигурация Django-приложения REST API."""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    """Определяет настройки приложения REST API."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
