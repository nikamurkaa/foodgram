"""Backend авторизации пользователя по логину или адресу электронной почты."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class UsernameOrEmailBackend(ModelBackend):
    """Аутентифицирует пользователя по username или email."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        """Возвращает активного пользователя с подходящими учётными данными."""

        user_model = get_user_model()
        login = username or kwargs.get(user_model.USERNAME_FIELD)
        if login is None or password is None:
            return None
        try:
            user = user_model._default_manager.get(
                Q(username=login) | Q(email__iexact=login)
            )
        except (
            user_model.DoesNotExist,
            user_model.MultipleObjectsReturned,
        ):
            user_model().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
