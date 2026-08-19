"""Настройки постраничной выдачи объектов API."""

from rest_framework.pagination import PageNumberPagination

from .constants import PAGE_SIZE


class FoodgramPagination(PageNumberPagination):
    """Разбивает выдачу API на страницы по шесть объектов."""

    page_size = PAGE_SIZE
    page_size_query_param = "limit"
