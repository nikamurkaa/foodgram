"""Команда загрузки витринных рецептов с фотографиями."""

import io
from pathlib import Path
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image

from recipes.constants import (
    IMAGE_DOWNLOAD_TIMEOUT,
    MAX_IMAGE_SIZE,
    PHOTO_URL_TEMPLATE,
    PHOTO_WIDTH,
)
from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from users.models import User

TAGS = (
    ("Завтрак", "breakfast"),
    ("Обед", "lunch"),
    ("Ужин", "dinner"),
    ("Десерт", "dessert"),
    ("Вегетарианское", "vegetarian"),
)

RECIPES = (
    {
        "name": "Воздушные панкейки с лесными ягодами",
        "author": "review",
        "photo_id": "yxZSAjyToP4",
        "photo_author": "Sam Moghadam Khamseh",
        "tags": ("breakfast", "dessert"),
        "cooking_time": 30,
        "text": (
            "Нежные панкейки с золотистой корочкой, свежей клубникой и "
            "голубикой. Смешайте сухие ингредиенты, отдельно взбейте молоко "
            "с яйцами и соедините обе смеси. Жарьте на сухой сковороде до "
            "появления пузырьков, переверните и подрумяньте. Подавайте "
            "горячими с ягодами и мёдом."
        ),
        "ingredients": (
            ("пшеничная мука", 220),
            ("молоко", 300),
            ("яйца куриные", 120),
            ("сахар", 35),
            ("сливочное масло", 40),
            ("клубника", 150),
            ("голубика", 100),
            ("мед", 50),
        ),
    },
    {
        "name": "Хрустящий салат с авокадо",
        "author": "review",
        "photo_id": "r8A-FTlLY3c",
        "photo_author": "Jonathan Ybema",
        "tags": ("lunch", "vegetarian"),
        "cooking_time": 15,
        "text": (
            "Лёгкий салат из хрустящих овощей и спелого авокадо. Нарежьте "
            "овощи крупными кусочками, добавьте листья салата и тонкие кольца "
            "красного лука. Заправьте оливковым маслом, посолите и аккуратно "
            "перемешайте непосредственно перед подачей."
        ),
        "ingredients": (
            ("салат романо", 150),
            ("помидоры", 200),
            ("огурцы", 150),
            ("авокадо", 200),
            ("лук красный", 50),
            ("оливковое масло", 30),
            ("соль", 5),
        ),
    },
    {
        "name": "Тыквенный крем-суп с нежными сливками",
        "author": "review",
        "photo_id": "JELuDsF96tA",
        "photo_author": "Elena Leya",
        "tags": ("lunch", "vegetarian"),
        "cooking_time": 45,
        "text": (
            "Бархатистый суп с насыщенным вкусом запечённой тыквы. Обжарьте "
            "лук и чеснок на сливочном масле, добавьте кубики тыквы и бульон. "
            "Варите до мягкости, измельчите блендером и влейте сливки. "
            "Прогрейте, не доводя до кипения."
        ),
        "ingredients": (
            ("тыква", 800),
            ("лук репчатый", 120),
            ("чеснок", 10),
            ("овощной бульон", 700),
            ("сливки 20%", 200),
            ("сливочное масло", 30),
            ("соль", 7),
        ),
    },
    {
        "name": "Паста с лососем в сливочном соусе",
        "author": "review",
        "photo_id": "sH5tnwlUbXc",
        "photo_author": "Brelyn Bashrum",
        "tags": ("lunch", "dinner"),
        "cooking_time": 35,
        "text": (
            "Итальянская паста с сочным лососем и сливочным соусом. Отварите "
            "спагетти до состояния аль денте. Быстро обжарьте лосося с "
            "чесноком, добавьте сливки и пармезан. Соедините с пастой, "
            "приправьте свежемолотым перцем и сразу подавайте."
        ),
        "ingredients": (
            ("спагетти", 350),
            ("лосось", 400),
            ("сливки 20%", 250),
            ("пармезан", 80),
            ("чеснок", 10),
            ("оливковое масло", 25),
            ("соль", 6),
            ("перец черный молотый", 2),
        ),
    },
    {
        "name": "Домашний бургер с говядиной и чеддером",
        "author": "chef1",
        "photo_id": "T3_qI9VLc9o",
        "photo_author": "Victoria Shes",
        "tags": ("lunch", "dinner"),
        "cooking_time": 40,
        "text": (
            "Сочный бургер с румяной котлетой, расплавленным чеддером и "
            "свежими овощами. Сформуйте котлеты и обжарьте по 4 минуты с "
            "каждой стороны. Подрумяньте булочки, смажьте соусами и соберите "
            "бургеры, добавляя салат, томаты и красный лук."
        ),
        "ingredients": (
            ("говядина", 600),
            ("булочки для гамбургеров", 4),
            ("чеддер", 160),
            ("помидоры", 120),
            ("лук красный", 80),
            ("салат", 80),
            ("кетчуп томатный", 60),
            ("горчица", 30),
        ),
    },
    {
        "name": "Овощная пицца с моцареллой",
        "author": "chef1",
        "photo_id": "q2nKKZ-Gqps",
        "photo_author": "Alonso Romero",
        "tags": ("lunch", "dinner", "vegetarian"),
        "cooking_time": 50,
        "text": (
            "Домашняя пицца с тонкой основой, томатным соусом и нежной "
            "моцареллой. Растяните тесто руками, смажьте соусом и разложите "
            "сыр, томаты, цукини и шпинат. Выпекайте при максимальной "
            "температуре до румяных бортиков, затем украсьте базиликом."
        ),
        "ingredients": (
            ("тесто для пиццы", 500),
            ("томатный соус", 180),
            ("моцарелла для пиццы", 250),
            ("помидоры", 150),
            ("цукини", 160),
            ("шпинат свежий", 80),
            ("базилик свежий", 20),
            ("оливковое масло", 20),
        ),
    },
    {
        "name": "Запечённая курица с овощами и розмарином",
        "author": "chef2",
        "photo_id": "wDtErSkmevs",
        "photo_author": "Tadahiro Higuchi",
        "tags": ("dinner",),
        "cooking_time": 75,
        "text": (
            "Ароматная курица с золотистой корочкой и запечёнными овощами. "
            "Натрите куриные бёдра солью, перцем, чесноком и розмарином. "
            "Разложите рядом картофель и морковь, сбрызните маслом и "
            "запекайте до мягкости овощей и прозрачного сока из курицы."
        ),
        "ingredients": (
            ("куриные бедра", 1000),
            ("картофель", 800),
            ("морковь", 300),
            ("чеснок", 20),
            ("розмарин", 10),
            ("оливковое масло", 40),
            ("соль", 8),
            ("перец черный молотый", 3),
        ),
    },
    {
        "name": "Клубничный чизкейк с голубикой",
        "author": "chef1",
        "photo_id": "Qbuto9p3weY",
        "photo_author": "Karolina Grabowska",
        "tags": ("dessert",),
        "cooking_time": 90,
        "text": (
            "Нежный сливочный чизкейк на хрустящей основе со свежими "
            "ягодами. Измельчите печенье, смешайте с маслом и утрамбуйте в "
            "форме. Взбейте сыр со сливками, сахаром и ванилью, выложите на "
            "основу и охладите. Перед подачей украсьте клубникой и голубикой."
        ),
        "ingredients": (
            ("творожный сыр", 600),
            ("печенье", 250),
            ("сливочное масло", 100),
            ("сливки 33-35%", 200),
            ("сахар", 150),
            ("клубника", 250),
            ("голубика", 100),
            ("ванильный экстракт", 5),
        ),
    },
)


class Command(BaseCommand):
    """Заменяет тестовые рецепты готовой витринной подборкой."""

    help = "Заменяет демонстрационные рецепты витринными рецептами с фото"

    def add_arguments(self, parser):
        """Добавляет путь к заранее загруженным изображениям."""

        parser.add_argument(
            "--image-dir",
            type=Path,
            help="Каталог с JPEG-файлами, названными по ID фотографий",
        )

    def handle(self, *args, **options):
        """Проверяет ресурсы и атомарно создаёт витринные рецепты."""

        users = self._get_users()
        ingredients = self._get_ingredients()
        images = self._load_images(options["image_dir"])

        with transaction.atomic():
            old_recipes = list(Recipe.objects.all())
            for recipe in old_recipes:
                if recipe.image:
                    recipe.image.delete(save=False)
            Recipe.objects.all().delete()

            tags = {
                slug: Tag.objects.get_or_create(name=name, slug=slug)[0]
                for name, slug in TAGS
            }
            for item in RECIPES:
                recipe = Recipe(
                    author=users[item["author"]],
                    name=item["name"],
                    text=item["text"],
                    cooking_time=item["cooking_time"],
                )
                filename = f'{item["photo_id"]}.jpg'
                recipe.image.save(
                    filename,
                    ContentFile(images[item["photo_id"]]),
                    save=False,
                )
                recipe.save()
                recipe.tags.set(tags[slug] for slug in item["tags"])
                RecipeIngredient.objects.bulk_create(
                    RecipeIngredient(
                        recipe=recipe,
                        ingredient=ingredients[name],
                        amount=amount,
                    )
                    for name, amount in item["ingredients"]
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Удалено рецептов: {len(old_recipes)}. "
                f"Создано рецептов: {len(RECIPES)}."
            )
        )
        for item in RECIPES:
            self.stdout.write(
                f'Фото: {item["photo_author"]} — '
                f'https://unsplash.com/photos/{item["photo_id"]}'
            )

    @staticmethod
    def _get_users():
        """Возвращает авторов подборки или сообщает об их отсутствии."""

        usernames = {item["author"] for item in RECIPES}
        users = User.objects.in_bulk(usernames, field_name="username")
        missing = usernames - users.keys()
        if missing:
            raise CommandError(
                "Не найдены авторы: " + ", ".join(sorted(missing))
            )
        return users

    @staticmethod
    def _get_ingredients():
        """Возвращает однозначные ингредиенты для всех рецептов."""

        names = {
            name for item in RECIPES for name, _amount in item["ingredients"]
        }
        ingredients = {}
        duplicates = set()
        for ingredient in Ingredient.objects.filter(name__in=names):
            if ingredient.name in ingredients:
                duplicates.add(ingredient.name)
            ingredients[ingredient.name] = ingredient
        if duplicates:
            raise CommandError(
                "Несколько единиц измерения у ингредиентов: "
                + ", ".join(sorted(duplicates))
            )
        missing = names - ingredients.keys()
        if missing:
            raise CommandError(
                "Не найдены ингредиенты: " + ", ".join(sorted(missing))
            )
        return ingredients

    def _load_images(self, image_dir):
        """Читает локальные изображения или загружает их из Unsplash."""

        images = {}
        for item in RECIPES:
            photo_id = item["photo_id"]
            if image_dir:
                filename = image_dir / f"{photo_id}.jpg"
                self.stdout.write(f"Чтение фотографии {filename}...")
                try:
                    data = filename.read_bytes()
                except OSError as error:
                    raise CommandError(
                        f"Не удалось прочитать фотографию {filename}: {error}"
                    ) from error
            else:
                self.stdout.write(f"Загрузка фотографии {photo_id}...")
                request = Request(
                    PHOTO_URL_TEMPLATE.format(
                        photo_id=photo_id, width=PHOTO_WIDTH
                    ),
                    headers={"User-Agent": "Foodgram/1.0"},
                )
                try:
                    with urlopen(
                        request, timeout=IMAGE_DOWNLOAD_TIMEOUT
                    ) as response:
                        data = response.read(MAX_IMAGE_SIZE + 1)
                except OSError as error:
                    raise CommandError(
                        "Не удалось загрузить фотографию "
                        f"{photo_id}: {error}"
                    ) from error
            if len(data) > MAX_IMAGE_SIZE:
                raise CommandError(
                    f"Фотография {photo_id} превышает допустимый размер."
                )
            try:
                Image.open(io.BytesIO(data)).verify()
            except (OSError, SyntaxError) as error:
                raise CommandError(
                    f"Файл {photo_id} не является изображением."
                ) from error
            images[photo_id] = data
        return images
