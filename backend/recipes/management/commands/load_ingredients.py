"""Команда загрузки справочника ингредиентов из JSON-файла."""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from recipes.models import Ingredient


class Command(BaseCommand):
    """Загружает ингредиенты без создания повторных записей."""

    help = "Идемпотентно загружает ингредиенты из JSON-файла"

    def add_arguments(self, parser):
        """Добавляет необязательный путь к исходному JSON-файлу."""

        parser.add_argument("--path", type=Path)

    def handle(self, *args, **options):
        """Находит источник и сохраняет отсутствующие ингредиенты."""

        candidates = (
            options["path"],
            settings.BASE_DIR / "data" / "ingredients.json",
            settings.BASE_DIR.parent / "data" / "ingredients.json",
        )
        source = next(
            (path for path in candidates if path and path.exists()),
            None,
        )
        if source is None:
            raise CommandError("Файл ingredients.json не найден.")
        with source.open(encoding="utf-8") as source_file:
            ingredients = json.load(source_file)
        created = 0
        for item in ingredients:
            _, was_created = Ingredient.objects.get_or_create(
                name=item["name"], measurement_unit=item["measurement_unit"]
            )
            created += was_created
        self.stdout.write(
            self.style.SUCCESS(
                f"Загружено {len(ingredients)} ингредиентов, "
                f"создано {created}."
            )
        )
