"""Настройки моделей рецептов в административной панели."""

from django.contrib import admin
from django.db.models import Count

from .models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)


class RecipeIngredientInline(admin.TabularInline):
    """Позволяет редактировать состав на странице рецепта."""

    model = RecipeIngredient
    extra = 1
    min_num = 1
    validate_min = True


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Настраивает список, поиск и фильтры рецептов."""

    list_display = ("name", "author", "favorite_count", "pub_date")
    search_fields = ("name", "author__username", "author__email")
    list_filter = ("tags",)
    filter_horizontal = ("tags",)
    inlines = (RecipeIngredientInline,)

    def get_queryset(self, request):
        """Добавляет к рецептам количество отметок избранного."""

        return (
            super()
            .get_queryset(request)
            .annotate(favorite_total=Count("favorites"))
        )

    @admin.display(
        description="Добавлений в избранное",
        ordering="favorite_total",
    )
    def favorite_count(self, recipe):
        """Возвращает число добавлений рецепта в избранное."""

        return recipe.favorite_total


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Настраивает список и поиск ингредиентов."""

    list_display = ("name", "measurement_unit")
    search_fields = ("name",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Настраивает список и поиск тегов."""

    list_display = ("name", "slug")
    search_fields = ("name", "slug")


@admin.register(Favorite)
@admin.register(ShoppingCart)
class UserRecipeRelationAdmin(admin.ModelAdmin):
    """Настраивает пользовательские связи с рецептами."""

    list_display = ("user", "recipe", "created_at")
    search_fields = ("user__username", "recipe__name")
