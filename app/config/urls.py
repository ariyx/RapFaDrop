from django.contrib import admin
from django.urls import include, path

from core.views import health

urlpatterns = [
    path("admin/ops/", include("operations.urls")),
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
]
