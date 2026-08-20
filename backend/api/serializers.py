"""Сериализаторы пользователей, рецептов и справочников Foodgram."""

from django.db import transaction
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)
from users.models import Subscription, User


class UserSerializer(serializers.ModelSerializer):
    """Преобразует пользователя и статус подписки в данные API."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(read_only=True, allow_null=True)

    class Meta:
        """Определяет доступные поля пользователя."""

        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "avatar",
        )

    def get_is_subscribed(self, author):
        """Проверяет подписку текущего пользователя на автора."""

        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and request.user.subscriptions.filter(author=author).exists()
        )


class AvatarSerializer(serializers.ModelSerializer):
    """Принимает и возвращает аватар пользователя."""

    avatar = Base64ImageField(required=True)

    class Meta:
        """Ограничивает сериализатор полем аватара."""

        model = User
        fields = ("avatar",)


class TagSerializer(serializers.ModelSerializer):
    """Преобразует тег в представление API."""

    class Meta:
        """Определяет поля тега."""

        model = Tag
        fields = ("id", "name", "slug")


class IngredientSerializer(serializers.ModelSerializer):
    """Преобразует ингредиент в представление API."""

    class Meta:
        """Определяет поля ингредиента."""

        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Возвращает ингредиент вместе с количеством в рецепте."""

    id = serializers.IntegerField(source="ingredient_id")
    name = serializers.CharField(source="ingredient.name")
    measurement_unit = serializers.CharField(
        source="ingredient.measurement_unit"
    )

    class Meta:
        """Определяет поля ингредиента в составе рецепта."""

        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Возвращает краткие данные рецепта для вложенных списков."""

    class Meta:
        """Определяет сокращённый набор полей рецепта."""

        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class RecipeReadSerializer(serializers.ModelSerializer):
    """Формирует полное представление рецепта для чтения."""

    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        source="recipe_ingredients", many=True, read_only=True
    )
    is_favorited = serializers.BooleanField(read_only=True, default=False)
    is_in_shopping_cart = serializers.BooleanField(
        read_only=True, default=False
    )

    class Meta:
        """Определяет поля полного представления рецепта."""

        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )


class IngredientAmountSerializer(serializers.ModelSerializer):
    """Проверяет ингредиент и его количество средствами модели."""

    id = serializers.PrimaryKeyRelatedField(
        source="ingredient", queryset=Ingredient.objects.all()
    )

    class Meta:
        """Определяет поля состава записываемого рецепта."""

        model = RecipeIngredient
        fields = ("id", "amount")


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Проверяет и сохраняет данные создаваемого рецепта."""

    ingredients = IngredientAmountSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField(required=True)

    class Meta:
        """Определяет поля записи рецепта."""

        model = Recipe
        fields = (
            "id",
            "ingredients",
            "tags",
            "image",
            "name",
            "text",
            "cooking_time",
        )
        read_only_fields = ("id",)
        extra_kwargs = {
            "name": {"allow_blank": False},
            "text": {"allow_blank": False},
        }

    def validate(self, attrs):
        """Проверяет наличие и уникальность тегов и ингредиентов."""

        errors = {}
        for field in ("ingredients", "tags"):
            if field not in self.initial_data:
                errors[field] = ["Обязательное поле."]
            elif not self.initial_data[field]:
                errors[field] = ["Список не может быть пустым."]
        if errors:
            raise serializers.ValidationError(errors)

        ingredients = attrs["ingredients"]
        ingredient_ids = [item["ingredient"].id for item in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            errors["ingredients"] = [
                "Ингредиенты не должны повторяться."
            ]

        tags = attrs["tags"]
        tag_ids = [tag.id for tag in tags]
        if len(tag_ids) != len(set(tag_ids)):
            errors["tags"] = ["Теги не должны повторяться."]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    @staticmethod
    def _set_ingredients(recipe, ingredients):
        """Сохраняет состав рецепта одним пакетным запросом."""

        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(recipe=recipe, **item) for item in ingredients
        )

    @transaction.atomic
    def create(self, validated_data):
        """Создаёт рецепт вместе с тегами и ингредиентами."""

        ingredients = validated_data.pop("ingredients")
        tags = validated_data.pop("tags")
        recipe = Recipe.objects.create(
            author=self.context["request"].user, **validated_data
        )
        recipe.tags.set(tags)
        self._set_ingredients(recipe, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        """Обновляет рецепт и полностью заменяет его состав."""

        ingredients = validated_data.pop("ingredients")
        tags = validated_data.pop("tags")
        instance = super().update(instance, validated_data)
        instance.tags.set(tags)
        instance.recipe_ingredients.all().delete()
        self._set_ingredients(instance, ingredients)
        return instance

    def to_representation(self, instance):
        """Возвращает записанный рецепт в формате для чтения."""

        return RecipeReadSerializer(instance, context=self.context).data


class UserWithRecipesSerializer(UserSerializer):
    """Добавляет к пользователю его рецепты и их количество."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(source="recipes.count")

    class Meta(UserSerializer.Meta):
        """Расширяет поля пользователя данными о рецептах."""

        fields = UserSerializer.Meta.fields + ("recipes", "recipes_count")

    def get_recipes(self, author):
        """Возвращает рецепты автора с необязательным лимитом."""

        recipes = author.recipes.all()
        request = self.context.get("request")
        raw_limit = (
            request.query_params.get("recipes_limit") if request else None
        )
        if raw_limit is not None:
            try:
                limit = max(0, int(raw_limit))
            except (TypeError, ValueError):
                limit = None
            if limit is not None:
                recipes = recipes[:limit]
        return RecipeMinifiedSerializer(recipes, many=True).data


class SubscriptionSerializer(serializers.ModelSerializer):
    """Создаёт подписку и возвращает профиль выбранного автора."""

    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        """Определяет участников подписки."""

        model = Subscription
        fields = ("user", "author")

    def validate(self, attrs):
        """Запрещает подписку на себя и повторную подписку."""

        if attrs["user"] == attrs["author"]:
            raise serializers.ValidationError(
                {"errors": "Нельзя подписаться на себя."}
            )
        if Subscription.objects.filter(**attrs).exists():
            raise serializers.ValidationError(
                {"errors": "Подписка уже существует."}
            )
        return attrs

    def to_representation(self, instance):
        """Возвращает автора в формате страницы подписок."""

        return UserWithRecipesSerializer(
            instance.author, context=self.context
        ).data


class UserRecipeRelationSerializer(serializers.ModelSerializer):
    """Содержит общую логику избранного и списка покупок."""

    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )
    duplicate_error = "Рецепт уже добавлен в список."

    def validate(self, attrs):
        """Запрещает повторное добавление рецепта в один список."""

        if self.Meta.model.objects.filter(**attrs).exists():
            raise serializers.ValidationError(
                {"errors": self.duplicate_error}
            )
        return attrs

    def to_representation(self, instance):
        """Возвращает добавленный рецепт в кратком формате."""

        return RecipeMinifiedSerializer(
            instance.recipe, context=self.context
        ).data


class FavoriteSerializer(UserRecipeRelationSerializer):
    """Создаёт и представляет запись избранного."""

    duplicate_error = "Рецепт уже добавлен в избранное."

    class Meta:
        """Определяет поля записи избранного."""

        model = Favorite
        fields = ("user", "recipe")


class ShoppingCartSerializer(UserRecipeRelationSerializer):
    """Создаёт и представляет запись списка покупок."""

    duplicate_error = "Рецепт уже добавлен в список покупок."

    class Meta:
        """Определяет поля записи списка покупок."""

        model = ShoppingCart
        fields = ("user", "recipe")
