"""Тесты объектных прав доступа REST API."""

from types import SimpleNamespace
from unittest import TestCase

from api import permissions


class IsUserOrReadOnlyTests(TestCase):
    """Проверяет защиту пользовательских профилей от чужих изменений."""

    def setUp(self):
        """Создаёт минимальные объекты запроса и пользователей."""

        self.owner = object()
        self.other_user = object()

    def has_permission(self, method, request_user, profile_owner):
        """Применяет реальное объектное право к тестовому запросу."""

        permission_class = getattr(
            permissions,
            "IsUserOrReadOnly",
            None,
        )
        self.assertIsNotNone(permission_class)
        request = SimpleNamespace(method=method, user=request_user)
        return permission_class().has_object_permission(
            request,
            view=None,
            obj=profile_owner,
        )

    def test_safe_methods_allow_reading_another_profile(self):
        """Публичное чтение чужого профиля остаётся доступным."""

        self.assertTrue(
            self.has_permission("GET", self.other_user, self.owner)
        )

    def test_owner_can_change_own_profile(self):
        """Владелец может изменить собственный профиль."""

        self.assertTrue(
            self.has_permission("PATCH", self.owner, self.owner)
        )

    def test_user_cannot_change_another_profile(self):
        """Пользователь не может изменить чужой профиль."""

        self.assertFalse(
            self.has_permission("PATCH", self.other_user, self.owner)
        )
