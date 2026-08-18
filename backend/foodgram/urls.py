"""Корневые URL-маршруты проекта Foodgram."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from api.views import short_link_redirect

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("s/<str:code>/", short_link_redirect, name="short-link"),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
