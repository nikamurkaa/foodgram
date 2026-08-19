"""Права доступа к объектам REST API."""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAuthorOrReadOnly(BasePermission):
    """Разрешает изменять объект только его автору."""

    def has_object_permission(self, request, view, obj):
        """Проверяет право пользователя на операцию с объектом."""

        return request.method in SAFE_METHODS or obj.author == request.user


class IsUserOrAdminOrReadOnly(BasePermission):
    """Разрешает читать профили всем, а изменять владельцу и админу."""

    def has_object_permission(self, request, view, obj):
        """Проверяет метод запроса и принадлежность профиля."""

        return request.method in SAFE_METHODS or (
            request.user.is_authenticated
            and (request.user == obj or request.user.is_staff)
        )
