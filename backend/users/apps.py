"""Конфигурация Django-приложения пользователей."""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Определяет настройки приложения пользователей."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "users"
    verbose_name = "Пользователи"
