"""Представления REST API для работы с данными Foodgram."""

from django.db.models import BooleanField, Exists, OuterRef, Sum, Value
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)
from users.models import Subscription, User

from .filters import IngredientFilter, RecipeFilter
from .pagination import FoodgramPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    AvatarSerializer,
    FavoriteSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    ShoppingCartSerializer,
    SubscriptionSerializer,
    TagSerializer,
    UserWithRecipesSerializer,
)


class UserViewSet(DjoserUserViewSet):
    """Дополняет пользовательские действия Djoser подписками и аватаром."""

    queryset = User.objects.all()
    pagination_class = FoodgramPagination

    @action(
        detail=False,
        methods=("get",),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def me(self, request, *args, **kwargs):
        """Возвращает профиль текущего пользователя средствами Djoser."""

        return super().me(request, *args, **kwargs)

    @action(
        detail=False,
        methods=("put",),
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=AvatarSerializer,
        url_path="me/avatar",
    )
    def avatar(self, request):
        """Устанавливает аватар текущего пользователя."""

        serializer = self.get_serializer(
            request.user, data=request.data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        """Удаляет файл аватара текущего пользователя."""

        if request.user.avatar:
            request.user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=("get",),
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=UserWithRecipesSerializer,
    )
    def subscriptions(self, request):
        """Возвращает авторов из подписок текущего пользователя."""

        authors = User.objects.filter(
            subscribers__user=request.user
        ).prefetch_related("recipes")
        page = self.paginate_queryset(authors)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=("post",),
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=SubscriptionSerializer,
    )
    def subscribe(self, request, **kwargs):
        """Создаёт подписку на выбранного автора."""

        author = get_object_or_404(User, pk=kwargs[self.lookup_field])
        serializer = self.get_serializer(data={"author": author.pk})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscription(self, request, **kwargs):
        """Удаляет подписку на выбранного автора."""

        author = get_object_or_404(User, pk=kwargs[self.lookup_field])
        deleted_count, _ = Subscription.objects.filter(
            user=request.user, author=author
        ).delete()
        if not deleted_count:
            return Response(
                {"errors": "Вы не подписаны на этого пользователя."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Предоставляет тегам доступ только для чтения."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Возвращает ингредиенты и поддерживает поиск по началу имени."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filterset_class = IngredientFilter
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """Обрабатывает рецепты и связанные пользовательские списки."""

    serializer_class = RecipeReadSerializer
    pagination_class = FoodgramPagination
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly,
    )
    filterset_class = RecipeFilter
    http_method_names = ("get", "post", "patch", "delete", "head", "options")

    def get_serializer_class(self):
        """Выбирает сериализатор записи для создания и изменения."""

        if self.action in ("create", "partial_update"):
            return RecipeWriteSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        """Формирует оптимизированную выборку и личные признаки."""

        queryset = Recipe.objects.select_related("author").prefetch_related(
            "tags", "recipe_ingredients__ingredient"
        )
        user = self.request.user
        if user.is_authenticated:
            return queryset.annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(user=user, recipe=OuterRef("pk"))
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(
                        user=user, recipe=OuterRef("pk")
                    )
                ),
            )
        return queryset.annotate(
            is_favorited=Value(False, output_field=BooleanField()),
            is_in_shopping_cart=Value(
                False, output_field=BooleanField()
            ),
        )

    @action(detail=True, methods=("get",), url_path="get-link")
    def get_link(self, request, pk=None):
        """Возвращает постоянную короткую ссылку на рецепт."""

        recipe = self.get_object()
        path = reverse("short-link", kwargs={"code": recipe.short_code})
        return Response({"short-link": request.build_absolute_uri(path)})

    @action(
        detail=True,
        methods=("post",),
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=FavoriteSerializer,
    )
    def favorite(self, request, pk=None):
        """Добавляет рецепт в избранное пользователя."""

        recipe = self.get_object()
        serializer = self.get_serializer(data={"recipe": recipe.pk})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        """Удаляет рецепт из избранного пользователя."""

        recipe = self.get_object()
        deleted_count, _ = Favorite.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if not deleted_count:
            return Response(
                {"errors": "Рецепт отсутствует в избранном."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=("post",),
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=ShoppingCartSerializer,
        url_path="shopping_cart",
    )
    def shopping_cart(self, request, pk=None):
        """Добавляет рецепт в список покупок пользователя."""

        recipe = self.get_object()
        serializer = self.get_serializer(data={"recipe": recipe.pk})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        """Удаляет рецепт из списка покупок пользователя."""

        recipe = self.get_object()
        deleted_count, _ = ShoppingCart.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if not deleted_count:
            return Response(
                {"errors": "Рецепт отсутствует в списке покупок."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=("get",),
        permission_classes=(permissions.IsAuthenticated,),
        url_path="download_shopping_cart",
    )
    def download_shopping_cart(self, request):
        """Формирует текстовый список покупок с суммами продуктов."""

        ingredients = (
            RecipeIngredient.objects.filter(
                recipe__shopping_carts__user=request.user
            )
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total=Sum("amount"))
            .order_by("ingredient__name", "ingredient__measurement_unit")
        )
        lines = [
            f"{item['ingredient__name']} "
            f"({item['ingredient__measurement_unit']}) — {item['total']}"
            for item in ingredients
        ]
        response = HttpResponse(
            "\n".join(lines), content_type="text/plain; charset=utf-8"
        )
        response["Content-Disposition"] = (
            'attachment; filename="shopping-list.txt"'
        )
        return response


def short_link_redirect(request, code):
    """Перенаправляет короткую ссылку на страницу рецепта."""

    recipe = get_object_or_404(Recipe, short_code=code)
    recipe_url = request.build_absolute_uri(f"/recipes/{recipe.pk}/")
    return HttpResponseRedirect(recipe_url)
