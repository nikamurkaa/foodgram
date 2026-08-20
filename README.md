# Foodgram

## Описание проекта

Foodgram — сервис для публикации рецептов и планирования покупок. Пользователи
могут создавать рецепты с фотографиями, выбирать ингредиенты и теги,
подписываться на авторов, добавлять блюда в избранное и формировать список
покупок. Количество одинаковых ингредиентов в списке суммируется, после чего
готовый перечень можно скачать в текстовом формате.

Основные возможности:

- регистрация пользователей и авторизация по токену;
- создание, редактирование и удаление собственных рецептов;
- фильтрация рецептов по автору, тегам, избранному и списку покупок;
- подписка на авторов и просмотр их рецептов;
- добавление рецептов в избранное и список покупок;
- загрузка аватара и изображения рецепта в Base64;
- создание коротких ссылок на рецепты;
- администрирование пользователей, рецептов, тегов и ингредиентов.

Развёрнутый проект: [kirta-security.ru](https://kirta-security.ru).

Административная панель:
[kirta-security.ru/admin/](https://kirta-security.ru/admin/)

- логин: `review`;
- пароль: `review1admin`;
- email: `review@admin.ru`.

## Стек технологий

| Компонент | Технологии |
| --- | --- |
| Backend | Python 3.11, Django 4.2, Django REST Framework 3.15 |
| API | Djoser, django-filter, Token Authentication, OpenAPI 3 |
| База данных | PostgreSQL 16, psycopg 3 |
| Frontend | React 17, React Router 5 |
| Web-сервер | Nginx 1.27, Gunicorn 23 |
| Инфраструктура | Docker, Docker Compose, named volumes |

## Развёртывание в Docker

Для запуска потребуются Git, Docker и Docker Compose. Production-конфигурация
Nginx использует домен `kirta-security.ru` и ожидает готовый сертификат
Let's Encrypt в каталоге
`/etc/letsencrypt/live/kirta-security.ru/`. Для другого домена необходимо
заменить домен и пути к сертификату в `infra/nginx.conf`.

1. Клонируйте репозиторий и перейдите в его каталог:

   ```bash
   git clone https://github.com/kindarufy/foodgram.git
   cd foodgram
   ```

2. Создайте файл окружения:

   ```bash
   cp infra/.env.example infra/.env
   ```

3. Укажите в `infra/.env` собственные значения:

   ```dotenv
   POSTGRES_DB=foodgram
   POSTGRES_USER=foodgram
   POSTGRES_PASSWORD=strong-database-password
   DB_HOST=db
   DB_PORT=5432
   SECRET_KEY=long-random-django-secret-key
   DEBUG=False
   ALLOWED_HOSTS=kirta-security.ru,127.0.0.1,localhost
   DEMO_USER_PASSWORD=strong-demo-user-password
   ```

4. Соберите и запустите сервисы:

   ```bash
   docker compose -f infra/docker-compose.yml up --build -d
   ```

   Контейнер backend автоматически применит миграции, соберёт статику и
   запустит Gunicorn. Nginx будет обслуживать frontend, API, статику и
   загруженные медиафайлы.

5. Проверьте состояние контейнеров:

   ```bash
   docker compose -f infra/docker-compose.yml ps
   docker compose -f infra/docker-compose.yml logs backend
   ```

Для остановки проекта без удаления данных выполните:

```bash
docker compose -f infra/docker-compose.yml down
```

## Наполнение базы данных

Сначала загрузите справочник ингредиентов из `data/ingredients.json`:

```bash
docker compose -f infra/docker-compose.yml exec backend \
  python manage.py load_ingredients
```

Затем создайте демонстрационных пользователей, теги и семь рецептов:

```bash
docker compose -f infra/docker-compose.yml exec backend \
  python manage.py seed_demo
```

Команды можно запускать повторно: они не создают дубликаты. `seed_demo`
создаёт администратора `review`, пользователей `chef1` и `chef2`; четыре из
семи демонстрационных рецептов принадлежат администратору.

Для замены демонстрационных рецептов на витринную подборку из восьми блюд с
фотографиями выполните:

```bash
docker compose -f infra/docker-compose.yml exec backend \
  python manage.py load_showcase_recipes
```

Команда загружает фотографии из Unsplash и заменяет существующие рецепты,
поэтому контейнеру backend потребуется доступ в интернет.

## Документация API

После развёртывания интерактивная документация ReDoc доступна по адресу:
[kirta-security.ru/api/docs/](https://kirta-security.ru/api/docs/).

Исходная OpenAPI-схема находится в файле
[`docs/openapi-schema.yml`](docs/openapi-schema.yml). Её также можно
импортировать в Swagger Editor, Postman или другой клиент с поддержкой
OpenAPI 3.

## Примеры запросов и ответов

Получение токена:

```bash
curl --request POST https://kirta-security.ru/api/auth/token/login/ \
  --header 'Content-Type: application/json' \
  --data '{
    "email": "review@admin.ru",
    "password": "review1admin"
  }'
```

Ответ:

```json
{
  "auth_token": "0123456789abcdef0123456789abcdef01234567"
}
```

Получение первой страницы рецептов:

```bash
curl 'https://kirta-security.ru/api/recipes/?limit=1'
```

Сокращённый пример ответа:

```json
{
  "count": 7,
  "next": "https://kirta-security.ru/api/recipes/?limit=1&page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Демонстрационный рецепт 1",
      "author": {
        "id": 1,
        "username": "review"
      },
      "is_favorited": false,
      "is_in_shopping_cart": false,
      "cooking_time": 11
    }
  ]
}
```

Добавление рецепта в избранное требует токен пользователя:

```bash
curl --request POST https://kirta-security.ru/api/recipes/1/favorite/ \
  --header 'Authorization: Token 0123456789abcdef0123456789abcdef01234567'
```

Ответ:

```json
{
  "id": 1,
  "name": "Демонстрационный рецепт 1",
  "image": "https://kirta-security.ru/media/recipes/images/demo-1.png",
  "cooking_time": 11
}
```

Полный перечень эндпоинтов, параметров и схем ответов приведён в ReDoc.

## Автор

[kindarufy](https://github.com/kindarufy)
