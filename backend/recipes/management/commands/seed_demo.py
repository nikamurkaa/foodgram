"""Команда создания демонстрационных пользователей и рецептов."""

import base64
import os

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from users.models import User

IMAGE = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD/"
    "//9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNo"
    "AAAAggCByxOyYQAAAABJRU5ErkJggg=="
)


class Command(BaseCommand):
    """Создаёт минимальный повторяемый набор демонстрационных данных."""

    help = "Идемпотентно создаёт демонстрационных пользователей и рецепты"

    @transaction.atomic
    def handle(self, *args, **options):
        """Создаёт пользователей, теги и по одному рецепту автора."""

        user_password = os.getenv("DEMO_USER_PASSWORD")
        admin_password = os.getenv("DEMO_ADMIN_PASSWORD")
        if not user_password or not admin_password:
            raise CommandError(
                "Задайте DEMO_USER_PASSWORD и DEMO_ADMIN_PASSWORD."
            )
        ingredient = Ingredient.objects.order_by("id").first()
        if ingredient is None:
            raise CommandError("Сначала выполните load_ingredients.")
        tags = [
            Tag.objects.get_or_create(name=name, slug=slug)[0]
            for name, slug in (
                ("Завтрак", "breakfast"),
                ("Обед", "lunch"),
                ("Ужин", "dinner"),
            )
        ]
        users = (
            self._user(
                "admin",
                "admin@example.com",
                "Администратор",
                "Foodgram",
                admin_password,
                is_staff=True,
                is_superuser=True,
            ),
            self._user(
                "chef1", "chef1@example.com", "Анна", "Повар", user_password
            ),
            self._user(
                "chef2", "chef2@example.com", "Иван", "Кулинар", user_password
            ),
        )
        for index, user in enumerate(users, start=1):
            recipe, _ = Recipe.objects.get_or_create(
                author=user,
                name=f"Демонстрационный рецепт {index}",
                defaults={
                    "text": "Рецепт для проверки работы приложения.",
                    "cooking_time": 10 + index,
                    "image": f"recipes/images/demo-{index}.png",
                },
            )
            if recipe.image:
                recipe.image.delete(save=False)
            recipe.image.save(
                f"demo-{index}.png",
                ContentFile(base64.b64decode(IMAGE)),
                save=True,
            )
            recipe.tags.set((tags[(index - 1) % len(tags)],))
            RecipeIngredient.objects.get_or_create(
                recipe=recipe,
                ingredient=ingredient,
                defaults={"amount": 100 * index},
            )
        self.stdout.write(
            self.style.SUCCESS("Демонстрационные данные готовы.")
        )

    @staticmethod
    def _user(username, email, first_name, last_name, password, **flags):
        """Создаёт или обновляет демонстрационного пользователя."""

        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                **flags,
            },
        )
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        for field, value in flags.items():
            setattr(user, field, value)
        user.set_password(password)
        user.save()
        return user
