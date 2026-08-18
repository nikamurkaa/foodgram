"""Представления REST API для работы с данными Foodgram."""

from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.db.models import BooleanField, Exists, OuterRef, Sum, Value
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)
from users.models import Subscription, User

from .pagination import FoodgramPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    AvatarSerializer,
    IngredientSerializer,
    PasswordSerializer,
    RecipeMinifiedSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    TagSerializer,
    TokenCreateSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserWithRecipesSerializer,
)
from .short_links import decode_base62, encode_base62


class UserViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Обрабатывает регистрацию, профили и подписки пользователей."""

    queryset = User.objects.all()
    pagination_class = FoodgramPagination

    def get_serializer_class(self):
        """Выбирает сериализатор для текущего действия."""

        if self.action == "create":
            return UserCreateSerializer
        if self.action in {"subscriptions", "subscribe"}:
            return UserWithRecipesSerializer
        return UserSerializer

    def get_permissions(self):
        """Ограничивает личные действия авторизованными пользователями."""

        if self.action in {
            "me",
            "avatar",
            "set_password",
            "subscriptions",
            "subscribe",
        }:
            return (permissions.IsAuthenticated(),)
        return (permissions.AllowAny(),)

    @action(detail=False, methods=("get",))
    def me(self, request):
        """Возвращает профиль текущего пользователя."""

        serializer = UserSerializer(
            request.user,
            context={"request": request},
        )
        return Response(serializer.data)

    @action(detail=False, methods=("put", "delete"), url_path="me/avatar")
    def avatar(self, request):
        """Устанавливает или удаляет аватар текущего пользователя."""

        user = request.user
        if request.method == "DELETE":
            if user.avatar:
                user.avatar.delete(save=False)
                user.avatar = None
                user.save(update_fields=("avatar",))
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = AvatarSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=("post",), url_path="set_password")
    def set_password(self, request):
        """Меняет пароль и удаляет ранее выданный токен."""

        serializer = PasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=("password",))
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=("get",))
    def subscriptions(self, request):
        """Возвращает авторов из подписок текущего пользователя."""

        authors = User.objects.filter(
            subscribers__user=request.user
        ).prefetch_related(
            "recipes",
        )
        page = self.paginate_queryset(authors)
        serializer = UserWithRecipesSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=("post", "delete"))
    def subscribe(self, request, pk=None):
        """Создаёт или удаляет подписку на выбранного автора."""

        author = get_object_or_404(User, pk=pk)
        relation = Subscription.objects.filter(
            user=request.user,
            author=author,
        )
        if request.method == "DELETE":
            if not relation.exists():
                return Response(
                    {"errors": "Вы не подписаны на этого пользователя."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            relation.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        if author == request.user or relation.exists():
            return Response(
                {"errors": "Нельзя создать такую подписку."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            Subscription.objects.create(user=request.user, author=author)
        except IntegrityError:
            return Response(
                {"errors": "Подписка уже существует."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = UserWithRecipesSerializer(
            author, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Предоставляет тегам доступ только для чтения."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Возвращает ингредиенты и поддерживает поиск по началу имени."""

    serializer_class = IngredientSerializer
    pagination_class = None

    def get_queryset(self):
        """Фильтрует ингредиенты по переданной части названия."""

        queryset = Ingredient.objects.all()
        name = self.request.query_params.get("name")
        if name:
            queryset = queryset.filter(name__startswith=name)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    """Обрабатывает рецепты и связанные пользовательские списки."""

    pagination_class = FoodgramPagination
    permission_classes = (IsAuthorOrReadOnly,)

    def get_permissions(self):
        """Выбирает права доступа с учётом текущего действия."""

        if self.action in {"list", "retrieve", "get_link"}:
            return (permissions.AllowAny(),)
        if self.action in {"update", "partial_update", "destroy"}:
            return (permissions.IsAuthenticated(), IsAuthorOrReadOnly())
        return (permissions.IsAuthenticated(),)

    def get_serializer_class(self):
        """Выбирает сериализатор для чтения или записи рецепта."""

        if self.action in {"create", "partial_update", "update"}:
            return RecipeWriteSerializer
        return RecipeReadSerializer

    def get_queryset(self):
        """Формирует и фильтрует оптимизированную выборку рецептов."""

        queryset = Recipe.objects.select_related("author").prefetch_related(
            "tags", "recipe_ingredients__ingredient"
        )
        user = self.request.user
        if user.is_authenticated:
            queryset = queryset.annotate(
                is_favorited_value=Exists(
                    Favorite.objects.filter(user=user, recipe=OuterRef("pk"))
                ),
                is_in_shopping_cart_value=Exists(
                    ShoppingCart.objects.filter(
                        user=user,
                        recipe=OuterRef("pk"),
                    )
                ),
            )
        else:
            queryset = queryset.annotate(
                is_favorited_value=Value(False, output_field=BooleanField()),
                is_in_shopping_cart_value=Value(
                    False, output_field=BooleanField()
                ),
            )

        author = self.request.query_params.get("author")
        if author:
            queryset = queryset.filter(author_id=author)
        tags = self.request.query_params.getlist("tags")
        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()
        queryset = self._apply_personal_filter(
            queryset, "is_favorited", "favorites__user"
        )
        return self._apply_personal_filter(
            queryset, "is_in_shopping_cart", "shopping_carts__user"
        )

    def _apply_personal_filter(self, queryset, parameter, relation):
        """Фильтрует рецепты по личному списку пользователя."""

        value = self.request.query_params.get(parameter)
        if value not in {"0", "1"}:
            return queryset
        if not self.request.user.is_authenticated:
            return queryset.none() if value == "1" else queryset
        lookup = {relation: self.request.user}
        if value == "1":
            return queryset.filter(**lookup)
        return queryset.exclude(**lookup)

    @action(detail=True, methods=("get",), url_path="get-link")
    def get_link(self, request, pk=None):
        """Возвращает постоянную короткую ссылку на рецепт."""

        recipe = self.get_object()
        path = reverse("short-link", kwargs={"code": encode_base62(recipe.id)})
        return Response({"short-link": request.build_absolute_uri(path)})

    def _relation_action(self, request, model, duplicate_message):
        """Добавляет или удаляет рецепт из пользовательского списка."""

        recipe = self.get_object()
        relation = model.objects.filter(user=request.user, recipe=recipe)
        if request.method == "DELETE":
            if not relation.exists():
                return Response(
                    {"errors": "Рецепт отсутствует в списке."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            relation.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        if relation.exists():
            return Response(
                {"errors": duplicate_message},
                status=status.HTTP_400_BAD_REQUEST,
            )
        model.objects.create(user=request.user, recipe=recipe)
        return Response(
            RecipeMinifiedSerializer(recipe).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=("post", "delete"))
    def favorite(self, request, pk=None):
        """Добавляет рецепт в избранное или удаляет его оттуда."""

        return self._relation_action(
            request, Favorite, "Рецепт уже добавлен в избранное."
        )

    @action(detail=True, methods=("post", "delete"), url_path="shopping_cart")
    def shopping_cart(self, request, pk=None):
        """Добавляет рецепт в список покупок или удаляет его."""

        return self._relation_action(
            request, ShoppingCart, "Рецепт уже добавлен в список покупок."
        )

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


class TokenLoginView(APIView):
    """Выдаёт токен по корректным email и паролю."""

    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        """Проверяет учётные данные и возвращает токен."""

        serializer = TokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["email"].lower(),
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {"non_field_errors": ["Неверный email или пароль."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"auth_token": token.key})


class TokenLogoutView(APIView):
    """Удаляет токен текущего пользователя."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        """Завершает текущую токен-сессию."""

        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def short_link_redirect(request, code):
    """Перенаправляет короткую ссылку на страницу рецепта."""

    try:
        recipe_id = decode_base62(code)
    except ValueError as error:
        raise Http404 from error
    get_object_or_404(Recipe, pk=recipe_id)
    return HttpResponseRedirect(f"/recipes/{recipe_id}")
