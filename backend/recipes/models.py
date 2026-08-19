"""Модели рецептов, ингредиентов, тегов и пользовательских списков."""

import secrets

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .constants import (
    INGREDIENT_NAME_MAX_LENGTH,
    MAX_COOKING_TIME,
    MAX_INGREDIENT_AMOUNT,
    MEASUREMENT_UNIT_MAX_LENGTH,
    MIN_COOKING_TIME,
    MIN_INGREDIENT_AMOUNT,
    RECIPE_NAME_MAX_LENGTH,
    SHORT_CODE_ALPHABET,
    SHORT_CODE_LENGTH,
    TAG_NAME_MAX_LENGTH,
    TAG_SLUG_MAX_LENGTH,
)


class Tag(models.Model):
    """Хранит уникальную тематическую метку рецепта."""

    name = models.CharField(
        "Название", max_length=TAG_NAME_MAX_LENGTH, unique=True
    )
    slug = models.SlugField(
        "Slug", max_length=TAG_SLUG_MAX_LENGTH, unique=True
    )

    class Meta:
        """Задаёт сортировку и русские названия модели."""

        ordering = ("name",)
        verbose_name = "тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        """Возвращает название тега."""

        return self.name


class Ingredient(models.Model):
    """Описывает продукт и его единицу измерения."""

    name = models.CharField(
        "Название", max_length=INGREDIENT_NAME_MAX_LENGTH
    )
    measurement_unit = models.CharField(
        "Единица измерения", max_length=MEASUREMENT_UNIT_MAX_LENGTH
    )

    class Meta:
        """Задаёт сортировку и уникальность ингредиента."""

        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("name", "measurement_unit"),
                name="unique_ingredient_measurement",
            )
        ]
        verbose_name = "ингредиент"
        verbose_name_plural = "Ингредиенты"

    def __str__(self):
        """Возвращает название продукта с единицей измерения."""

        return f"{self.name} ({self.measurement_unit})"


class Recipe(models.Model):
    """Хранит рецепт с автором, изображением и составом."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipes",
        verbose_name="Автор",
    )
    name = models.CharField("Название", max_length=RECIPE_NAME_MAX_LENGTH)
    image = models.ImageField("Изображение", upload_to="recipes/images/")
    text = models.TextField("Описание")
    ingredients = models.ManyToManyField(
        Ingredient, through="RecipeIngredient", related_name="recipes"
    )
    tags = models.ManyToManyField(Tag, related_name="recipes")
    cooking_time = models.PositiveSmallIntegerField(
        "Время приготовления",
        validators=(
            MinValueValidator(MIN_COOKING_TIME),
            MaxValueValidator(MAX_COOKING_TIME),
        ),
    )
    pub_date = models.DateTimeField("Дата публикации", auto_now_add=True)
    short_code = models.CharField(
        "Короткий код",
        max_length=SHORT_CODE_LENGTH,
        unique=True,
        editable=False,
    )

    class Meta:
        """Задаёт сортировку и ограничения рецепта."""

        ordering = ("-pub_date", "-id")
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    cooking_time__range=(
                        MIN_COOKING_TIME,
                        MAX_COOKING_TIME,
                    )
                ),
                name="recipe_cooking_time_valid_range",
            )
        ]
        verbose_name = "рецепт"
        verbose_name_plural = "Рецепты"

    def __str__(self):
        """Возвращает название рецепта."""

        return self.name

    @classmethod
    def generate_short_code(cls):
        """Создаёт свободный случайный код для короткой ссылки."""

        while True:
            code = "".join(
                secrets.choice(SHORT_CODE_ALPHABET)
                for _ in range(SHORT_CODE_LENGTH)
            )
            if not cls.objects.filter(short_code=code).exists():
                return code

    def save(self, *args, **kwargs):
        """Создаёт короткий код один раз и сохраняет рецепт."""

        if not self.short_code:
            self.short_code = self.generate_short_code()
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = tuple(update_fields) + (
                    "short_code",
                )
        return super().save(*args, **kwargs)


class RecipeIngredient(models.Model):
    """Связывает рецепт с ингредиентом и его количеством."""

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="recipe_ingredients"
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, related_name="recipe_amounts"
    )
    amount = models.PositiveSmallIntegerField(
        "Количество",
        validators=(
            MinValueValidator(MIN_INGREDIENT_AMOUNT),
            MaxValueValidator(MAX_INGREDIENT_AMOUNT),
        ),
    )

    class Meta:
        """Гарантирует уникальность ингредиента внутри рецепта."""

        constraints = [
            models.UniqueConstraint(
                fields=("recipe", "ingredient"),
                name="unique_recipe_ingredient",
            ),
            models.CheckConstraint(
                check=models.Q(
                    amount__range=(
                        MIN_INGREDIENT_AMOUNT,
                        MAX_INGREDIENT_AMOUNT,
                    )
                ),
                name="recipe_ingredient_amount_valid_range",
            ),
        ]
        verbose_name = "ингредиент рецепта"
        verbose_name_plural = "Ингредиенты рецепта"


class Favorite(models.Model):
    """Хранит рецепты, добавленные пользователем в избранное."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="favorites"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Запрещает повторное добавление рецепта в избранное."""

        constraints = [
            models.UniqueConstraint(
                fields=("user", "recipe"), name="unique_favorite"
            )
        ]
        verbose_name = "избранный рецепт"
        verbose_name_plural = "Избранное"


class ShoppingCart(models.Model):
    """Хранит рецепты из списка покупок пользователя."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shopping_cart",
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="shopping_carts"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Запрещает повторное добавление рецепта в покупки."""

        constraints = [
            models.UniqueConstraint(
                fields=("user", "recipe"), name="unique_shopping_cart"
            )
        ]
        verbose_name = "покупка"
        verbose_name_plural = "Список покупок"
