# Foodgram

Foodgram — сервис публикации рецептов, подписок, избранного и списка покупок.
Frontend поставляется готовым, backend реализован на Django REST Framework и
использует только PostgreSQL.

## Запуск

Единая конфигурация предназначена для сервера `kirta-security.ru` и ожидает
готовый сертификат Let's Encrypt в `/etc/letsencrypt`. Создайте файл окружения
и замените тестовые секреты:

```bash
cp infra/.env.example infra/.env
```

Соберите и запустите четыре сервиса:

```bash
docker compose -f infra/docker-compose.yml up --build -d
```

Загрузите ингредиенты и демонстрационные данные:

```bash
docker compose -f infra/docker-compose.yml exec backend python manage.py load_ingredients
docker compose -f infra/docker-compose.yml exec backend python manage.py seed_demo
```

После запуска доступны:

- приложение: <https://kirta-security.ru/>;
- API: <https://kirta-security.ru/api/>;
- документация API: <https://kirta-security.ru/api/docs/>;
- административная панель: <https://kirta-security.ru/admin/>.

## Проверки

```bash
docker compose -f infra/docker-compose.yml exec backend python manage.py test
docker compose -f infra/docker-compose.yml exec backend python manage.py check
docker compose -f infra/docker-compose.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f infra/docker-compose.yml exec backend flake8 . --exclude=migrations --max-line-length=88
```

Для полной проверки API импортируйте
`postman_collection/foodgram.postman_collection.json` в Postman и запустите
коллекцию против `http://localhost`.

Настройки CI/CD и публикация образов намеренно не входят в текущую
конфигурацию.

## Production HTTPS

После выпуска сертификата Let's Encrypt в `/etc/letsencrypt` production-запуск
выполняется единственным compose-файлом:

```bash
docker compose -f infra/docker-compose.yml up -d
```

Основная конфигурация Nginx обслуживает ACME webroot из `infra/certbot/www`,
перенаправляет HTTP на HTTPS и использует сертификат из `/etc/letsencrypt`.
Скрипт
`infra/certbot/deploy-hook.sh` перезагружает Nginx после автоматического
продления сертификата.
