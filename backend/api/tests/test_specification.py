"""Проверки соответствия API опубликованной спецификации Foodgram."""

import shutil
import tempfile

from django.test import override_settings
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from users.models import User

IMAGE = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD/"
    "//9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNo"
    "AAAAggCByxOyYQAAAABJRU5ErkJggg=="
)
TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class SpecificationEndpointTests(APITestCase):
    """Проверяет успешные и ошибочные ответы каждого endpoint."""

    @classmethod
    def tearDownClass(cls):
        """Удаляет временные изображения после всех тестов класса."""

        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        """Создаёт пользователей, справочники и один рецепт."""

        self.user = User.objects.create_user(
            email="spec-user@example.com",
            username="spec-user",
            first_name="Иван",
            last_name="Тестов",
            password="StrongPass123",
        )
        self.author = User.objects.create_user(
            email="spec-author@example.com",
            username="spec-author",
            first_name="Анна",
            last_name="Повар",
            password="StrongPass123",
        )
        self.tag = Tag.objects.create(name="Завтрак", slug="breakfast")
        self.ingredient = Ingredient.objects.create(
            name="Сахар", measurement_unit="г"
        )
        self.recipe = Recipe.objects.create(
            author=self.author,
            name="Тестовый рецепт",
            image="recipes/images/spec.png",
            text="Описание",
            cooking_time=10,
        )
        self.recipe.tags.add(self.tag)
        RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient,
            amount=10,
        )

    def authorize(self, user=None):
        """Авторизует клиент токеном выбранного пользователя."""

        token, _ = Token.objects.get_or_create(user=user or self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return token

    def recipe_payload(self, **updates):
        """Возвращает корректное тело запроса для рецепта."""

        payload = {
            "ingredients": [{"id": self.ingredient.id, "amount": 20}],
            "tags": [self.tag.id],
            "image": IMAGE,
            "name": "Новый рецепт",
            "text": "Подробное описание",
            "cooking_time": 20,
        }
        payload.update(updates)
        return payload

    def test_public_reference_and_user_endpoints(self):
        """Проверяет публичное чтение, 404 и запрещённые методы."""

        successful_urls = (
            "/api/users/",
            f"/api/users/{self.user.id}/",
            "/api/tags/",
            f"/api/tags/{self.tag.id}/",
            "/api/ingredients/",
            f"/api/ingredients/{self.ingredient.id}/",
            "/api/recipes/",
            f"/api/recipes/{self.recipe.id}/",
            f"/api/recipes/{self.recipe.id}/get-link/",
        )
        for url in successful_urls:
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url).status_code,
                    status.HTTP_200_OK,
                )

        missing_urls = (
            "/api/users/999999/",
            "/api/tags/999999/",
            "/api/ingredients/999999/",
            "/api/recipes/999999/",
            "/api/recipes/999999/get-link/",
        )
        for url in missing_urls:
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url).status_code,
                    status.HTTP_404_NOT_FOUND,
                )

        self.authorize()
        user_url = f"/api/users/{self.user.id}/"
        for method in (self.client.put, self.client.patch, self.client.delete):
            with self.subTest(method=method.__name__):
                self.assertEqual(
                    method(user_url, {}, format="json").status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                )
        self.assertEqual(
            self.client.post("/api/tags/", {}).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.post("/api/ingredients/", {}).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.post("/api/users/reset_password/", {}).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_registration_token_and_current_user_codes(self):
        """Проверяет регистрацию, токены, me и их ошибки доступа."""

        registration_url = "/api/users/"
        user_data = {
            "email": "registered@example.com",
            "username": "registered",
            "first_name": "Новый",
            "last_name": "Пользователь",
            "password": "AnotherPass123",
        }
        self.assertEqual(
            self.client.post(
                registration_url, {}, format="json"
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.client.post(
                registration_url, user_data, format="json"
            ).status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            self.client.post(
                registration_url, user_data, format="json"
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        login_url = "/api/auth/token/login/"
        self.assertEqual(
            self.client.post(login_url, {}, format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.client.post(
                login_url,
                {"email": user_data["email"], "password": "wrong"},
                format="json",
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        login = self.client.post(
            login_url,
            {
                "email": user_data["email"],
                "password": user_data["password"],
            },
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        token = login.data["auth_token"]

        protected_urls = (
            "/api/users/me/",
            "/api/users/subscriptions/",
            "/api/recipes/download_shopping_cart/",
        )
        for url in protected_urls:
            with self.subTest(url=url):
                self.client.credentials()
                self.assertEqual(
                    self.client.get(url).status_code,
                    status.HTTP_401_UNAUTHORIZED,
                )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(
            self.client.get("/api/users/me/").status_code,
            status.HTTP_200_OK,
        )
        for method in (self.client.put, self.client.patch, self.client.delete):
            with self.subTest(method=method.__name__):
                self.assertEqual(
                    method("/api/users/me/", {}, format="json").status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                )
        self.assertEqual(
            self.client.post("/api/auth/token/logout/").status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertEqual(
            self.client.get("/api/users/me/").status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_avatar_and_password_codes(self):
        """Проверяет аватар и смену пароля с кодами 400 и 401."""

        avatar_url = "/api/users/me/avatar/"
        self.assertEqual(
            self.client.put(
                avatar_url, {"avatar": IMAGE}, format="json"
            ).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.client.delete(avatar_url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.authorize()
        self.assertEqual(
            self.client.put(
                avatar_url, {"avatar": "not-an-image"}, format="json"
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.client.put(
                avatar_url, {"avatar": IMAGE}, format="json"
            ).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.delete(avatar_url).status_code,
            status.HTTP_204_NO_CONTENT,
        )

        password_url = "/api/users/set_password/"
        self.assertEqual(
            self.client.post(
                password_url,
                {
                    "current_password": "wrong",
                    "new_password": "ChangedPass123",
                },
                format="json",
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        changed = self.client.post(
            password_url,
            {
                "current_password": "StrongPass123",
                "new_password": "ChangedPass123",
            },
            format="json",
        )
        self.assertEqual(changed.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            self.client.get("/api/users/me/").status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_recipe_write_permissions_and_validation_codes(self):
        """Проверяет 400, 401, 403, 404 и 405 для записи рецептов."""

        recipe_url = f"/api/recipes/{self.recipe.id}/"
        self.assertEqual(
            self.client.post(
                "/api/recipes/", self.recipe_payload(), format="json"
            ).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.client.patch(
                recipe_url, self.recipe_payload(), format="json"
            ).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.client.delete(recipe_url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.authorize()
        self.assertEqual(
            self.client.patch(
                recipe_url, self.recipe_payload(), format="json"
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(recipe_url).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.put(
                recipe_url, self.recipe_payload(), format="json"
            ).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.patch(
                "/api/recipes/999999/", self.recipe_payload(), format="json"
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )

        invalid_payloads = (
            self.recipe_payload(ingredients=[]),
            self.recipe_payload(tags=[]),
            self.recipe_payload(cooking_time=0),
            self.recipe_payload(
                ingredients=[{"id": self.ingredient.id, "amount": 0}]
            ),
            self.recipe_payload(
                ingredients=[
                    {"id": self.ingredient.id, "amount": 1},
                    {"id": self.ingredient.id, "amount": 2},
                ]
            ),
            self.recipe_payload(tags=[self.tag.id, self.tag.id]),
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                self.assertEqual(
                    self.client.post(
                        "/api/recipes/", payload, format="json"
                    ).status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

        created = self.client.post(
            "/api/recipes/", self.recipe_payload(), format="json"
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            set(created.data),
            {
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
            },
        )

    def test_owner_update_and_delete_codes(self):
        """Проверяет обязательные связи, PATCH автора и удаление."""

        self.authorize(self.author)
        recipe_url = f"/api/recipes/{self.recipe.id}/"
        self.assertEqual(
            self.client.patch(
                recipe_url, {"name": "Без связей"}, format="json"
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        updated = self.client.patch(
            recipe_url,
            {
                "name": "Новое название",
                "ingredients": [
                    {"id": self.ingredient.id, "amount": 30}
                ],
                "tags": [self.tag.id],
            },
            format="json",
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data["name"], "Новое название")
        self.assertEqual(
            self.client.delete(recipe_url).status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertEqual(
            self.client.get(recipe_url).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_favorite_and_cart_codes(self):
        """Проверяет полный цикл избранного и списка покупок."""

        favorite_url = f"/api/recipes/{self.recipe.id}/favorite/"
        cart_url = f"/api/recipes/{self.recipe.id}/shopping_cart/"
        for url in (favorite_url, cart_url):
            with self.subTest(url=url, method="post"):
                self.assertEqual(
                    self.client.post(url).status_code,
                    status.HTTP_401_UNAUTHORIZED,
                )
            with self.subTest(url=url, method="delete"):
                self.assertEqual(
                    self.client.delete(url).status_code,
                    status.HTTP_401_UNAUTHORIZED,
                )

        self.authorize()
        for url in (favorite_url, cart_url):
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.post(url).status_code,
                    status.HTTP_201_CREATED,
                )
                self.assertEqual(
                    self.client.post(url).status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
                self.assertEqual(
                    self.client.delete(url).status_code,
                    status.HTTP_204_NO_CONTENT,
                )
                self.assertEqual(
                    self.client.delete(url).status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
        self.assertEqual(
            self.client.post(
                "/api/recipes/999999/favorite/"
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        shopping_file = self.client.get(
            "/api/recipes/download_shopping_cart/"
        )
        self.assertEqual(shopping_file.status_code, status.HTTP_200_OK)
        self.assertTrue(
            shopping_file["Content-Type"].startswith("text/plain")
        )

    def test_subscription_codes(self):
        """Проверяет доступ, валидацию и удаление подписки."""

        subscribe_url = f"/api/users/{self.author.id}/subscribe/"
        self.assertEqual(
            self.client.post(subscribe_url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.client.delete(subscribe_url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.authorize()
        self.assertEqual(
            self.client.post(
                f"/api/users/{self.user.id}/subscribe/"
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.client.post(
                "/api/users/999999/subscribe/"
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        subscribed = self.client.post(subscribe_url)
        self.assertEqual(subscribed.status_code, status.HTTP_201_CREATED)
        self.assertIn("recipes", subscribed.data)
        self.assertEqual(
            self.client.post(subscribe_url).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.client.get(
                "/api/users/subscriptions/?recipes_limit=1"
            ).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.delete(subscribe_url).status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertEqual(
            self.client.delete(subscribe_url).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_filters_pagination_and_short_redirect(self):
        """Проверяет фильтры, пагинацию и перенаправление ссылки."""

        response = self.client.get(
            f"/api/recipes/?author={self.author.id}"
            f"&tags={self.tag.slug}&limit=1"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            self.client.get(
                "/api/recipes/?is_favorited=1"
            ).data["count"],
            0,
        )
        self.assertEqual(
            self.client.get("/api/recipes/?page=999999").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.get("/api/recipes/?tags=unknown").status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        short_link = self.client.get(
            f"/api/recipes/{self.recipe.id}/get-link/"
        ).data["short-link"]
        short_path = short_link.replace("http://testserver", "")
        redirect = self.client.get(short_path)
        self.assertEqual(redirect.status_code, status.HTTP_302_FOUND)
        self.assertEqual(
            redirect["Location"],
            f"http://testserver/recipes/{self.recipe.id}/",
        )
        self.assertEqual(
            self.client.get("/s/unknown-code/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
