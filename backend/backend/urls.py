from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/market/", include("market.urls")),
    path("api/journal/", include("journal.urls")),
]
