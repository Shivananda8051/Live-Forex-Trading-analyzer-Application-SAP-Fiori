from django.contrib import admin

from .models import Trade


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ("pair", "direction", "entry_price", "result", "pnl", "trade_score", "created_at")
    list_filter = ("pair", "direction", "result", "session")
    search_fields = ("pair", "notes")
