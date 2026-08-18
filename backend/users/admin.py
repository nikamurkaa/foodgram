"""Настройки пользователей и подписок в административной панели."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Subscription, User


@admin.register(User)
class FoodgramUserAdmin(UserAdmin):
    """Добавляет данные Foodgram в стандартную панель пользователя."""

    list_display = ("username", "email", "first_name", "last_name", "is_staff")
    search_fields = ("username", "email")
    fieldsets = UserAdmin.fieldsets + (("Аватар", {"fields": ("avatar",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Обязательные данные",
            {"fields": ("email", "first_name", "last_name", "avatar")},
        ),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Настраивает отображение и поиск подписок."""

    list_display = ("user", "author", "created_at")
    search_fields = ("user__username", "author__username")
