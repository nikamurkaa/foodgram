"""Фильтры справочников и рецептов Foodgram."""

from django_filters import rest_framework as filters

from recipes.models import Ingredient, Recipe


class IngredientFilter(filters.FilterSet):
    """Фильтрует ингредиенты по началу названия без учёта регистра."""

    name = filters.CharFilter(method="filter_name")

    class Meta:
        """Связывает фильтр с моделью ингредиента."""

        model = Ingredient
        fields = ("name",)

    def filter_name(self, queryset, name, value):
        """Возвращает ингредиенты, начинающиеся с переданного текста."""

        return queryset.filter(name__istartswith=value)


class RecipeFilter(filters.FilterSet):
    """Фильтрует рецепты по тегам, автору и личным спискам."""

    tags = filters.AllValuesMultipleFilter(field_name="tags__slug")
    author = filters.NumberFilter(field_name="author_id")
    is_favorited = filters.BooleanFilter(method="filter_is_favorited")
    is_in_shopping_cart = filters.BooleanFilter(
        method="filter_is_in_shopping_cart"
    )

    class Meta:
        """Определяет параметры фильтрации рецептов."""

        model = Recipe
        fields = (
            "tags",
            "author",
            "is_favorited",
            "is_in_shopping_cart",
        )

    def filter_is_favorited(self, queryset, name, value):
        """Оставляет рецепты из избранного текущего пользователя."""

        if not value:
            return queryset
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        return queryset.filter(favorites__user=user)

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """Оставляет рецепты из корзины текущего пользователя."""

        if not value:
            return queryset
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        return queryset.filter(shopping_carts__user=user)
