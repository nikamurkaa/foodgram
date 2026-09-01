# Foodgram

Full-stack сервис для публикации рецептов и планирования покупок с REST API на **Django REST Framework**, React-интерфейсом и PostgreSQL.

Foodgram позволяет пользователям публиковать рецепты с фотографиями и ингредиентами, подписываться на авторов, сохранять понравившиеся блюда и формировать общий список покупок. Backend реализует пользовательскую модель, права доступа, фильтрацию, работу с изображениями и связанные пользовательские коллекции.

## Возможности

- регистрация и токен-аутентификация пользователей;
- создание, редактирование и удаление собственных рецептов;
- загрузка аватара и изображения рецепта;
- теги и ингредиенты;
- фильтрация рецептов по автору, тегам, избранному и списку покупок;
- подписки на авторов;
- избранные рецепты;
- список покупок с автоматическим суммированием одинаковых ингредиентов;
- выгрузка списка покупок в текстовом формате;
- короткие ссылки на рецепты;
- административная панель Django;
- OpenAPI/ReDoc-документация;
- Docker Compose для запуска frontend, backend, PostgreSQL и Nginx.

## Стек технологий

| Компонент | Технологии |
| --- | --- |
| Backend | Python, Django 4.2, Django REST Framework 3.15 |
| Authentication | Djoser, Token Authentication |
| Filtering | django-filter |
| Database | PostgreSQL 16, psycopg 3 |
| Frontend | React 17, React Router |
| Web server | Gunicorn, Nginx |
| Infrastructure | Docker, Docker Compose, named volumes |
| API docs | OpenAPI 3, ReDoc |

## Backend-архитектура

```text
backend/
├── api/        # serializers, views, filters, permissions, pagination
├── recipes/    # рецепты, ингредиенты, теги и пользовательские списки
├── users/      # пользовательская модель и подписки
├── foodgram/   # настройки Django-проекта
└── manage.py
```

REST API построено на ViewSet/Serializer-подходе DRF. Для рецептов используется объектное разрешение `IsAuthorOrReadOnly`: читать данные могут все пользователи, а изменение и удаление разрешено только автору объекта.

## Основные API-сценарии

| Сценарий | Endpoint |
| --- | --- |
| Рецепты | `/api/recipes/` |
| Пользователи | `/api/users/` |
| Теги | `/api/tags/` |
| Ингредиенты | `/api/ingredients/` |
| Подписки | `/api/users/subscriptions/` |
| Избранное | `/api/recipes/{id}/favorite/` |
| Список покупок | `/api/recipes/{id}/shopping_cart/` |
| Скачать список покупок | `/api/recipes/download_shopping_cart/` |
| Получить токен | `/api/auth/token/login/` |

Полная OpenAPI-схема находится в [`docs/openapi-schema.yml`](docs/openapi-schema.yml). После запуска Docker-окружения ReDoc доступен по адресу `http://localhost/api/docs/`.

## Запуск через Docker Compose

Клонируйте репозиторий:

```bash
git clone https://github.com/nikamurkaa/foodgram.git
cd foodgram
```

Создайте файл окружения:

```bash
cp infra/.env.example infra/.env
```

Пример конфигурации:

```dotenv
POSTGRES_DB=foodgram
POSTGRES_USER=foodgram
POSTGRES_PASSWORD=change-me
DB_HOST=db
DB_PORT=5432
SECRET_KEY=change-me-to-a-long-random-value
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
DEMO_USER_PASSWORD=change-me
```

Соберите и запустите сервисы:

```bash
docker compose -f infra/docker-compose.yml up -d --build
```

Проверьте состояние контейнеров:

```bash
docker compose -f infra/docker-compose.yml ps
```

После запуска интерфейс доступен по адресу `http://localhost`, API — по `http://localhost/api/`.

Остановить проект:

```bash
docker compose -f infra/docker-compose.yml down
```

## Наполнение базы данных

Загрузить ингредиенты:

```bash
docker compose -f infra/docker-compose.yml exec backend \
  python manage.py load_ingredients
```

Создать демонстрационные данные:

```bash
docker compose -f infra/docker-compose.yml exec backend \
  python manage.py seed_demo
```

Для демонстрационной подборки рецептов также предусмотрена команда:

```bash
docker compose -f infra/docker-compose.yml exec backend \
  python manage.py load_showcase_recipes
```

## Примеры API

Получить токен:

```bash
curl --request POST http://localhost/api/auth/token/login/ \
  --header 'Content-Type: application/json' \
  --data '{
    "email": "user@example.com",
    "password": "your-password"
  }'
```

Получить первую страницу рецептов:

```bash
curl 'http://localhost/api/recipes/?limit=5'
```

Добавить рецепт в избранное:

```bash
curl --request POST http://localhost/api/recipes/1/favorite/ \
  --header 'Authorization: Token <auth_token>'
```

## Проверка качества кода

Backend-зависимости устанавливаются из `backend/requirements.txt`.

```bash
cd backend
python -m pip install -r requirements.txt
flake8 .
```

Для функциональной проверки API в репозитории также есть [`postman_collection/`](postman_collection/).

## Структура проекта

```text
foodgram/
├── backend/             # Django REST API
├── frontend/            # React-приложение
├── infra/               # Docker Compose и Nginx
├── data/                # исходные данные ингредиентов
├── docs/                # OpenAPI/ReDoc
├── postman_collection/  # ручная проверка API
└── README.md
```

## Автор

[Николь Журбенко](https://github.com/nikamurkaa)

Проект выполнен в рамках курса **«Python-разработчик» Яндекс Практикума**.
