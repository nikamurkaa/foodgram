"""Модели пользователей и подписок проекта Foodgram."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import F, Q


class User(AbstractUser):
    """Расширяет пользователя Django обязательным email и аватаром."""

    email = models.EmailField("Адрес электронной почты", unique=True)
    first_name = models.CharField("Имя", max_length=150)
    last_name = models.CharField("Фамилия", max_length=150)
    avatar = models.ImageField(
        "Аватар", upload_to="users/", blank=True, null=True
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        """Задаёт сортировку и русские названия пользователя."""

        ordering = ("username",)
        verbose_name = "пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        """Возвращает имя пользователя."""

        return self.username


class Subscription(models.Model):
    """Описывает подписку пользователя на автора рецептов."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="subscriptions"
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="subscribers"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Запрещает дубликаты и подписку пользователя на себя."""

        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "author"), name="unique_subscription"
            ),
            models.CheckConstraint(
                check=~Q(user=F("author")), name="prevent_self_subscription"
            ),
        ]
        verbose_name = "подписка"
        verbose_name_plural = "Подписки"

    def __str__(self):
        """Возвращает читаемое направление подписки."""

        return f"{self.user} → {self.author}"
