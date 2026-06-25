from django.contrib import admin

from .models import (
    Alert,
    CandleData,
    ChartDrawing,
    NewsEvent,
    PatternOccurrence,
    PatternTemplate,
    UserSettings,
)


@admin.register(ChartDrawing)
class ChartDrawingAdmin(admin.ModelAdmin):
    list_display = ("pair", "timeframe", "tool_type", "color", "created_at")
    list_filter = ("pair", "timeframe", "tool_type")


@admin.register(PatternTemplate)
class PatternTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "pair", "timeframe", "lookback_candles", "created_at")
    list_filter = ("pair", "timeframe")


@admin.register(PatternOccurrence)
class PatternOccurrenceAdmin(admin.ModelAdmin):
    list_display = ("template", "found_at", "similarity_score", "outcome_pips", "outcome_direction")
    list_filter = ("outcome_direction",)


@admin.register(NewsEvent)
class NewsEventAdmin(admin.ModelAdmin):
    list_display = ("currency", "event_name", "time", "importance")
    list_filter = ("currency", "importance")


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("alert_type", "pair", "message", "triggered_at", "acknowledged")
    list_filter = ("alert_type", "acknowledged")


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ("default_risk_pct", "swing_lookback", "alert_sound", "alert_browser")
