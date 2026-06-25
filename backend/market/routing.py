"""WebSocket URL routing."""

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/pair/(?P<symbol>\w+)/$", consumers.MarketConsumer.as_asgi()),
    re_path(r"ws/overview/$", consumers.OverviewConsumer.as_asgi()),
    re_path(r"ws/alerts/$", consumers.AlertConsumer.as_asgi()),
]
