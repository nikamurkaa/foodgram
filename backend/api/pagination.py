"""Настройки постраничной выдачи объектов API."""

from rest_framework.pagination import PageNumberPagination


class FoodgramPagination(PageNumberPagination):
    """Разбивает выдачу API на страницы по шесть объектов."""

    page_size = 6
    page_size_query_param = "limit"
    max_page_size = 100
