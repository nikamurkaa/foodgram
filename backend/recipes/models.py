"""Модели рецептов, ингредиентов, тегов и пользовательских списков."""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Tag(models.Model):
    """Хранит уникальную тематическую метку рецепта."""

    name = models.CharField("Название", max_length=32, unique=True)
    slug = models.SlugField("Slug", max_length=32, unique=True)

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

    name = models.CharField("Название", max_length=128)
    measurement_unit = models.CharField("Единица измерения", max_length=64)

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
    name = models.CharField("Название", max_length=256)
    image = models.ImageField("Изображение", upload_to="recipes/images/")
    text = models.TextField("Описание")
    ingredients = models.ManyToManyField(
        Ingredient, through="RecipeIngredient", related_name="recipes"
    )
    tags = models.ManyToManyField(Tag, related_name="recipes")
    cooking_time = models.PositiveSmallIntegerField(
        "Время приготовления", validators=(MinValueValidator(1),)
    )
    pub_date = models.DateTimeField("Дата публикации", auto_now_add=True)

    class Meta:
        """Задаёт сортировку и ограничения рецепта."""

        ordering = ("-pub_date", "-id")
        constraints = [
            models.CheckConstraint(
                check=models.Q(cooking_time__gte=1),
                name="recipe_cooking_time_gte_1",
            )
        ]
        verbose_name = "рецепт"
        verbose_name_plural = "Рецепты"

    def __str__(self):
        """Возвращает название рецепта."""

        return self.name


class RecipeIngredient(models.Model):
    """Связывает рецепт с ингредиентом и его количеством."""

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="recipe_ingredients"
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, related_name="recipe_amounts"
    )
    amount = models.PositiveIntegerField(
        "Количество", validators=(MinValueValidator(1),)
    )

    class Meta:
        """Гарантирует уникальность ингредиента внутри рецепта."""

        constraints = [
            models.UniqueConstraint(
                fields=("recipe", "ingredient"),
                name="unique_recipe_ingredient",
            ),
            models.CheckConstraint(
                check=models.Q(amount__gte=1),
                name="recipe_ingredient_amount_gte_1",
            ),
        ]
        verbose_name = "ингредиент рецепта"
        verbose_name_plural = "Ингредиенты рецепта"


class UserRecipeRelation(models.Model):
    """Служит основой для пользовательских списков рецептов."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Объявляет модель абстрактной."""

        abstract = True


class Favorite(UserRecipeRelation):
    """Хранит рецепты, добавленные пользователем в избранное."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="favorites"
    )

    class Meta:
        """Запрещает повторное добавление рецепта в избранное."""

        constraints = [
            models.UniqueConstraint(
                fields=("user", "recipe"), name="unique_favorite"
            )
        ]
        verbose_name = "избранный рецепт"
        verbose_name_plural = "Избранное"


class ShoppingCart(UserRecipeRelation):
    """Хранит рецепты из списка покупок пользователя."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shopping_cart",
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="shopping_carts"
    )

    class Meta:
        """Запрещает повторное добавление рецепта в покупки."""

        constraints = [
            models.UniqueConstraint(
                fields=("user", "recipe"), name="unique_shopping_cart"
            )
        ]
        verbose_name = "покупка"
        verbose_name_plural = "Список покупок"
