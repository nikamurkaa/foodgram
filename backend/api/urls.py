"""Маршруты REST API проекта Foodgram."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    IngredientViewSet,
    RecipeViewSet,
    TagViewSet,
    TokenLoginView,
    TokenLogoutView,
    UserViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="users")
router.register("tags", TagViewSet, basename="tags")
router.register("ingredients", IngredientViewSet, basename="ingredients")
router.register("recipes", RecipeViewSet, basename="recipes")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/token/login/", TokenLoginView.as_view(), name="token-login"),
    path("auth/token/logout/", TokenLogoutView.as_view(), name="token-logout"),
]
