"""Интеграционные тесты основных сценариев REST API Foodgram."""

import shutil
import tempfile

from django.test import override_settings
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from api.pagination import FoodgramPagination
from api.serializers import RecipeWriteSerializer
from recipes.constants import (
    MAX_COOKING_TIME,
    MAX_INGREDIENT_AMOUNT,
    SHORT_CODE_LENGTH,
)
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)
from users.models import Subscription, User

IMAGE = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD/"
    "//9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNo"
    "AAAAggCByxOyYQAAAABJRU5ErkJggg=="
)
TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class FoodgramAPITests(APITestCase):
    """Проверяет пользовательские и рецептурные сценарии API."""

    @classmethod
    def tearDownClass(cls):
        """Удаляет временные медиафайлы после выполнения тестов."""

        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        """Создаёт пользователей и базовые справочные данные."""

        self.user = User.objects.create_user(
            email="user@example.com",
            username="user",
            first_name="Иван",
            last_name="Иванов",
            password="StrongPass123",
        )
        self.author = User.objects.create_user(
            email="author@example.com",
            username="author",
            first_name="Анна",
            last_name="Повар",
            password="StrongPass123",
        )
        self.breakfast = Tag.objects.create(name="Завтрак", slug="breakfast")
        self.dinner = Tag.objects.create(name="Ужин", slug="dinner")
        self.sugar = Ingredient.objects.create(
            name="Сахар", measurement_unit="г"
        )
        self.recipe = self.create_recipe(
            self.author,
            "Каша",
            self.breakfast,
            5,
        )

    def create_recipe(self, author, name, tag, amount):
        """Создаёт рецепт для использования в тестовом сценарии."""

        recipe = Recipe.objects.create(
            author=author,
            name=name,
            image="recipes/images/test.png",
            text="Описание рецепта",
            cooking_time=10,
        )
        recipe.tags.add(tag)
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=self.sugar, amount=amount
        )
        return recipe

    def authorize(self, user=None):
        """Авторизует тестовый клиент токеном выбранного пользователя."""

        token, _ = Token.objects.get_or_create(user=user or self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def recipe_payload(self, tags=None, ingredients=None, **updates):
        """Формирует корректные данные рецепта с нужными изменениями."""

        payload = {
            "ingredients": ingredients
            or [{"id": self.sugar.id, "amount": 10}],
            "tags": tags or [self.breakfast.id],
            "image": IMAGE,
            "name": "Новый рецепт",
            "text": "Подробное описание",
            "cooking_time": 15,
        }
        payload.update(updates)
        return payload

    def test_registration_login_and_current_user(self):
        """Проверяет регистрацию, вход и получение своего профиля."""

        registration = self.client.post(
            "/api/users/",
            {
                "email": "new@example.com",
                "username": "new-user",
                "first_name": "Новый",
                "last_name": "Пользователь",
                "password": "AnotherPass123",
            },
            format="json",
        )
        self.assertEqual(registration.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", registration.data)
        login = self.client.post(
            "/api/auth/token/login/",
            {"email": "new@example.com", "password": "AnotherPass123"},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {login.data['auth_token']}"
        )
        me = self.client.get("/api/users/me/")
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["email"], "new@example.com")
        self.assertIsNone(me.data["avatar"])

    def test_change_password_invalidates_token(self):
        """Проверяет смену пароля и отзыв старого токена."""

        self.authorize()
        response = self.client.post(
            "/api/users/set_password/",
            {
                "current_password": "StrongPass123",
                "new_password": "ChangedPass123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_public_profiles_and_read_only_me(self):
        """Проверяет публичные профили и единственный GET-метод me."""

        users = self.client.get("/api/users/")
        profile = self.client.get(f"/api/users/{self.author.id}/")
        self.assertEqual(users.status_code, status.HTTP_200_OK)
        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        self.authorize()
        forbidden_method = self.client.patch(
            "/api/users/me/", {"first_name": "Другое"}, format="json"
        )
        self.assertEqual(
            forbidden_method.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_avatar_lifecycle(self):
        """Проверяет установку и удаление аватара."""

        self.authorize()
        created = self.client.put(
            "/api/users/me/avatar/", {"avatar": IMAGE}, format="json"
        )
        self.assertEqual(created.status_code, status.HTTP_200_OK)
        self.assertTrue(created.data["avatar"])
        deleted = self.client.delete("/api/users/me/avatar/")
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertFalse(self.user.avatar)

    def test_recipe_list_pagination_and_or_tag_filter(self):
        """Проверяет пагинацию и объединение фильтров тегов через ИЛИ."""

        second = self.create_recipe(self.author, "Суп", self.dinner, 7)
        response = self.client.get(
            f"/api/recipes/?limit=1&tags={self.breakfast.slug}"
            f"&tags={self.dinner.slug}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], second.id)
        self.assertEqual(FoodgramPagination.page_size, 6)
        self.assertIsNone(FoodgramPagination.max_page_size)

    def test_create_recipe_and_reject_duplicate_ingredients(self):
        """Проверяет создание рецепта и запрет повторов в составе."""

        self.authorize()
        created = self.client.post(
            "/api/recipes/", self.recipe_payload(), format="json"
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["author"]["id"], self.user.id)
        duplicated = self.client.post(
            "/api/recipes/",
            self.recipe_payload(
                ingredients=[
                    {"id": self.sugar.id, "amount": 1},
                    {"id": self.sugar.id, "amount": 2},
                ]
            ),
            format="json",
        )
        self.assertEqual(duplicated.status_code, status.HTTP_400_BAD_REQUEST)

    def test_write_serializer_represents_instance_without_view(self):
        """Проверяет представление рецепта без повторного запроса из view."""

        data = RecipeWriteSerializer().to_representation(self.recipe)

        self.assertFalse(data["is_favorited"])
        self.assertFalse(data["is_in_shopping_cart"])

    def test_only_author_can_update_or_delete_recipe(self):
        """Проверяет запрет редактирования чужого рецепта."""

        self.authorize()
        denied = self.client.patch(
            f"/api/recipes/{self.recipe.id}/",
            self.recipe_payload(image=None),
            format="json",
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.authorize(self.author)
        missing_fields = self.client.patch(
            f"/api/recipes/{self.recipe.id}/",
            {"name": "Новое имя"},
            format="json",
        )
        self.assertEqual(
            missing_fields.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        updated = self.client.patch(
            f"/api/recipes/{self.recipe.id}/",
            {
                "name": "Новое имя",
                "tags": [self.breakfast.id],
                "ingredients": [{"id": self.sugar.id, "amount": 8}],
            },
            format="json",
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        put_response = self.client.put(
            f"/api/recipes/{self.recipe.id}/",
            self.recipe_payload(),
            format="json",
        )
        self.assertEqual(
            put_response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_recipe_numeric_limits(self):
        """Проверяет допустимые границы времени и количества."""

        self.authorize()
        accepted = self.client.post(
            "/api/recipes/",
            self.recipe_payload(
                cooking_time=MAX_COOKING_TIME,
                ingredients=[
                    {"id": self.sugar.id, "amount": MAX_INGREDIENT_AMOUNT}
                ],
            ),
            format="json",
        )
        self.assertEqual(accepted.status_code, status.HTTP_201_CREATED)
        excessive_time = self.client.post(
            "/api/recipes/",
            self.recipe_payload(cooking_time=MAX_COOKING_TIME + 1),
            format="json",
        )
        excessive_amount = self.client.post(
            "/api/recipes/",
            self.recipe_payload(
                ingredients=[
                    {
                        "id": self.sugar.id,
                        "amount": MAX_INGREDIENT_AMOUNT + 1,
                    }
                ]
            ),
            format="json",
        )
        self.assertEqual(
            excessive_time.status_code, status.HTTP_400_BAD_REQUEST
        )
        self.assertEqual(
            excessive_amount.status_code, status.HTTP_400_BAD_REQUEST
        )

    def test_favorites_and_anonymous_personal_filter(self):
        """Проверяет избранное и личный фильтр для гостя."""

        self.authorize()
        added = self.client.post(f"/api/recipes/{self.recipe.id}/favorite/")
        self.assertEqual(added.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Favorite.objects.filter(user=self.user).exists())
        filtered = self.client.get("/api/recipes/?is_favorited=1")
        self.assertEqual(filtered.data["count"], 1)
        self.client.credentials()
        anonymous = self.client.get("/api/recipes/?is_favorited=1")
        self.assertEqual(anonymous.status_code, status.HTTP_200_OK)
        self.assertEqual(anonymous.data["count"], 0)

    def test_relation_actions_validate_and_delete(self):
        """Проверяет сериализаторы и отдельные DELETE-действия связей."""

        self.authorize()
        favorite_url = f"/api/recipes/{self.recipe.id}/favorite/"
        self.assertEqual(
            self.client.post(favorite_url).status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            self.client.post(favorite_url).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.client.delete(favorite_url).status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertEqual(
            self.client.delete(favorite_url).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        cart_url = f"/api/recipes/{self.recipe.id}/shopping_cart/"
        self.assertEqual(
            self.client.post(cart_url).status_code,
            status.HTTP_201_CREATED,
        )
        filtered = self.client.get(
            "/api/recipes/?is_in_shopping_cart=1"
        )
        self.assertEqual(filtered.data["count"], 1)
        self.assertEqual(
            self.client.delete(cart_url).status_code,
            status.HTTP_204_NO_CONTENT,
        )

    def test_shopping_list_aggregates_ingredients(self):
        """Проверяет суммирование продуктов в списке покупок."""

        second = self.create_recipe(self.author, "Пирог", self.dinner, 10)
        ShoppingCart.objects.create(user=self.user, recipe=self.recipe)
        ShoppingCart.objects.create(user=self.user, recipe=second)
        self.authorize()
        response = self.client.get("/api/recipes/download_shopping_cart/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content.decode(), "Сахар (г) — 15")
        self.assertIn("shopping-list.txt", response["Content-Disposition"])

    def test_subscriptions_include_limited_recipes(self):
        """Проверяет подписку и ограничение вложенных рецептов."""

        self.create_recipe(self.author, "Пирог", self.dinner, 10)
        self.authorize()
        subscribed = self.client.post(
            f"/api/users/{self.author.id}/subscribe/?recipes_limit=1"
        )
        self.assertEqual(subscribed.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(subscribed.data["recipes"]), 1)
        self.assertTrue(
            Subscription.objects.filter(
                user=self.user,
                author=self.author,
            ).exists()
        )
        duplicate = self.client.post(f"/api/users/{self.author.id}/subscribe/")
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self_subscription = self.client.post(
            f"/api/users/{self.user.id}/subscribe/"
        )
        self.assertEqual(
            self_subscription.status_code, status.HTTP_400_BAD_REQUEST
        )
        deleted = self.client.delete(
            f"/api/users/{self.author.id}/subscribe/"
        )
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        missing = self.client.delete(
            f"/api/users/{self.author.id}/subscribe/"
        )
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)

    def test_short_link_is_stable_and_redirects(self):
        """Проверяет постоянство и перенаправление короткой ссылки."""

        first = self.client.get(f"/api/recipes/{self.recipe.id}/get-link/")
        self.recipe.name = "Изменённое название"
        self.recipe.save(update_fields=("name",))
        second = self.client.get(f"/api/recipes/{self.recipe.id}/get-link/")
        self.assertEqual(first.data["short-link"], second.data["short-link"])
        self.assertEqual(len(self.recipe.short_code), SHORT_CODE_LENGTH)
        path = first.data["short-link"].replace("http://testserver", "")
        redirect = self.client.get(path)
        self.assertEqual(redirect.status_code, status.HTTP_302_FOUND)
        self.assertEqual(
            redirect["Location"],
            f"http://testserver/recipes/{self.recipe.id}/",
        )

    def test_tags_and_ingredients_are_read_only(self):
        """Проверяет запрет изменения справочников через API."""

        self.authorize()
        tag = self.client.post(
            "/api/tags/", {"name": "Полдник", "slug": "snack"}
        )
        ingredient = self.client.post(
            "/api/ingredients/", {"name": "Соль", "measurement_unit": "г"}
        )
        self.assertEqual(tag.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(
            ingredient.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_ingredient_name_filter_is_case_insensitive(self):
        """Проверяет регистронезависимый поиск ингредиентов по началу."""

        Ingredient.objects.create(name="Соль", measurement_unit="г")
        response = self.client.get("/api/ingredients/?name=со")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["name"] for item in response.data], ["Соль"])
