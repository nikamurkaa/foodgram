"""Конфигурация Django-приложения рецептов."""

from django.apps import AppConfig


class RecipesConfig(AppConfig):
    """Определяет настройки приложения рецептов."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "recipes"
    verbose_name = "Рецепты"
