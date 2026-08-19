"""Маршруты REST API проекта Foodgram."""

from django.urls import include, path
from rest_framework.permissions import IsAuthenticated
from rest_framework.routers import DefaultRouter

from .serializers import (
    AvatarSerializer,
    SubscriptionSerializer,
    UserWithRecipesSerializer,
)
from .views import IngredientViewSet, RecipeViewSet, TagViewSet, UserViewSet

router = DefaultRouter()
router.register("tags", TagViewSet, basename="tags")
router.register("ingredients", IngredientViewSet, basename="ingredients")
router.register("recipes", RecipeViewSet, basename="recipes")

urlpatterns = [
    path(
        "users/",
        UserViewSet.as_view({"get": "list", "post": "create"}),
        name="users-list",
    ),
    path(
        "users/me/",
        UserViewSet.as_view(
            {"get": "me"},
            permission_classes=(IsAuthenticated,),
        ),
        name="users-me",
    ),
    path(
        "users/me/avatar/",
        UserViewSet.as_view(
            {"put": "avatar", "delete": "delete_avatar"},
            permission_classes=(IsAuthenticated,),
            serializer_class=AvatarSerializer,
        ),
        name="users-avatar",
    ),
    path(
        "users/subscriptions/",
        UserViewSet.as_view(
            {"get": "subscriptions"},
            permission_classes=(IsAuthenticated,),
            serializer_class=UserWithRecipesSerializer,
        ),
        name="users-subscriptions",
    ),
    path(
        "users/set_password/",
        UserViewSet.as_view({"post": "set_password"}),
        name="users-set-password",
    ),
    path(
        "users/<int:id>/subscribe/",
        UserViewSet.as_view(
            {"post": "subscribe", "delete": "delete_subscription"},
            permission_classes=(IsAuthenticated,),
            serializer_class=SubscriptionSerializer,
        ),
        name="users-subscribe",
    ),
    path(
        "users/<int:id>/",
        UserViewSet.as_view({"get": "retrieve"}),
        name="users-detail",
    ),
    path("", include(router.urls)),
    path("auth/", include("djoser.urls.authtoken")),
]
