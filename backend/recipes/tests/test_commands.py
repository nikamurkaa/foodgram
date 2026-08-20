"""Тесты команд загрузки данных и ограничений базы."""

import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from users.models import Subscription, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CommandAndConstraintTests(TestCase):
    """Проверяет команды управления и ограничения моделей."""

    @classmethod
    def tearDownClass(cls):
        """Удаляет временные медиафайлы после тестов."""

        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_load_ingredients_is_idempotent(self):
        """Проверяет повторный запуск загрузки ингредиентов."""

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "ingredients.json"
            source.write_text(
                json.dumps(
                    [{"name": "Сахар", "measurement_unit": "г"}],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            call_command("load_ingredients", path=source)
            call_command("load_ingredients", path=source)
        self.assertEqual(Ingredient.objects.count(), 1)

    def test_seed_demo_is_idempotent(self):
        """Проверяет повторный запуск создания демонстрационных данных."""

        Ingredient.objects.create(name="Сахар", measurement_unit="г")
        environment = {
            "DEMO_USER_PASSWORD": "DemoUserPass123",
        }
        with patch.dict(os.environ, environment):
            call_command("seed_demo")
            call_command("seed_demo")
        self.assertEqual(User.objects.count(), 3)
        self.assertEqual(Recipe.objects.count(), 7)
        self.assertEqual(Tag.objects.count(), 3)
        review = User.objects.get(username="review")
        self.assertEqual(review.email, "review@admin.ru")
        self.assertTrue(review.is_staff)
        self.assertTrue(review.is_superuser)
        self.assertTrue(review.check_password("review1admin"))
        self.assertEqual(review.recipes.count(), 4)

    def test_database_constraints_reject_duplicates_and_self_subscription(
        self,
    ):
        """Проверяет уникальность состава и запрет подписки на себя."""

        user = User.objects.create_user(
            email="test@example.com",
            username="test-user",
            first_name="Тест",
            last_name="Пользователь",
            password="StrongPass123",
        )
        tag = Tag.objects.create(name="Обед", slug="lunch")
        ingredient = Ingredient.objects.create(
            name="Сахар",
            measurement_unit="г",
        )
        recipe = Recipe.objects.create(
            author=user,
            name="Рецепт",
            image="recipes/images/test.png",
            text="Описание",
            cooking_time=5,
        )
        recipe.tags.add(tag)
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=ingredient, amount=1
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            RecipeIngredient.objects.create(
                recipe=recipe, ingredient=ingredient, amount=2
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Subscription.objects.create(user=user, author=user)
