"""Сериализаторы пользователей, рецептов и справочников Foodgram."""

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
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


class UserCreateSerializer(serializers.ModelSerializer):
    """Проверяет данные и создаёт нового пользователя."""

    password = serializers.CharField(write_only=True)

    class Meta:
        """Определяет поля регистрации пользователя."""

        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "password",
        )
        read_only_fields = ("id",)

    def validate_password(self, value):
        """Проверяет пароль стандартными валидаторами Django."""

        validate_password(value)
        return value

    def validate_email(self, value):
        """Приводит адрес электронной почты к нижнему регистру."""

        return value.lower()

    def create(self, validated_data):
        """Создаёт пользователя с безопасно сохранённым паролем."""

        return User.objects.create_user(**validated_data)


class AvatarSerializer(serializers.ModelSerializer):
    """Принимает и возвращает аватар пользователя."""

    avatar = Base64ImageField(required=True)

    class Meta:
        """Ограничивает сериализатор полем аватара."""

        model = User
        fields = ("avatar",)


class PasswordSerializer(serializers.Serializer):
    """Проверяет данные для смены пароля пользователя."""

    current_password = serializers.CharField()
    new_password = serializers.CharField()

    def validate_current_password(self, value):
        """Проверяет совпадение текущего пароля."""

        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль.")
        return value

    def validate_new_password(self, value):
        """Проверяет надёжность нового пароля."""

        validate_password(value, self.context["request"].user)
        return value


class TokenCreateSerializer(serializers.Serializer):
    """Проверяет учётные данные для получения токена."""

    email = serializers.EmailField()
    password = serializers.CharField()


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
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

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

    def get_is_favorited(self, recipe):
        """Проверяет наличие рецепта в избранном пользователя."""

        annotated = getattr(recipe, "is_favorited_value", None)
        if annotated is not None:
            return annotated
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and recipe.favorites.filter(user=request.user).exists()
        )

    def get_is_in_shopping_cart(self, recipe):
        """Проверяет наличие рецепта в списке покупок."""

        annotated = getattr(recipe, "is_in_shopping_cart_value", None)
        if annotated is not None:
            return annotated
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and recipe.shopping_carts.filter(user=request.user).exists()
        )


class IngredientAmountSerializer(serializers.Serializer):
    """Проверяет идентификатор и количество ингредиента."""

    id = serializers.PrimaryKeyRelatedField(
        source="ingredient", queryset=Ingredient.objects.all()
    )
    amount = serializers.IntegerField(min_value=1)


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Проверяет и сохраняет данные создаваемого рецепта."""

    ingredients = IngredientAmountSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField(required=True)

    class Meta:
        """Определяет обязательные поля записи рецепта."""

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
        """Проверяет полноту данных при создании и обновлении."""

        required = ("ingredients", "tags", "name", "text", "cooking_time")
        if "image" in self.initial_data and not self.initial_data["image"]:
            raise serializers.ValidationError(
                {"image": ["Изображение не может быть пустым."]}
            )
        if self.instance:
            missing = [
                field for field in required if field not in self.initial_data
            ]
            if missing:
                raise serializers.ValidationError(
                    {field: ["Обязательное поле."] for field in missing}
                )
        return attrs

    def validate_ingredients(self, value):
        """Запрещает пустой список и повторение ингредиентов."""

        if not value:
            raise serializers.ValidationError(
                "Добавьте хотя бы один ингредиент."
            )
        ids = [item["ingredient"].id for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                "Ингредиенты не должны повторяться."
            )
        return value

    def validate_tags(self, value):
        """Запрещает пустой список и повторение тегов."""

        if not value:
            raise serializers.ValidationError("Добавьте хотя бы один тег.")
        ids = [tag.id for tag in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Теги не должны повторяться.")
        return value

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
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        instance.save()
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
    """Преобразует связь подписчика с автором."""

    class Meta:
        """Определяет поля подписки."""

        model = Subscription
        fields = ("user", "author")
