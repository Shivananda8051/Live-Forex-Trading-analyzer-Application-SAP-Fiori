from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"trades", views.TradeViewSet)

urlpatterns = [
    path("analytics/", views.analytics, name="analytics"),
    path("score-validation/", views.score_validation, name="score-validation"),
    path("", include(router.urls)),
]
