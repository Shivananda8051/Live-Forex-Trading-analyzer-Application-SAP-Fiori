from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"drawings", views.ChartDrawingViewSet)
router.register(r"patterns", views.PatternTemplateViewSet)
router.register(r"alerts", views.AlertViewSet)

urlpatterns = [
    path("candles/", views.candles, name="candles"),
    path("analysis/", views.analysis, name="analysis"),
    path("ticks/", views.ticks, name="ticks"),
    path("account/", views.account_info, name="account-info"),
    path("session/", views.session_info, name="session-info"),
    path("news/", views.news_events, name="news-events"),
    path("risk/", views.risk_calculate, name="risk-calculate"),
    path("settings/", views.user_settings, name="user-settings"),
    path("", include(router.urls)),
]
