from django.db import models


class CandleData(models.Model):
    """Cached OHLCV candle data from MT5."""

    pair = models.CharField(max_length=10, db_index=True)
    timeframe = models.CharField(max_length=5, db_index=True)  # M1, M5, M15, H1, H4, D1
    time = models.DateTimeField(db_index=True)
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.FloatField(default=0)

    class Meta:
        unique_together = ("pair", "timeframe", "time")
        ordering = ["-time"]

    def __str__(self):
        return f"{self.pair} {self.timeframe} {self.time}"


class ChartDrawing(models.Model):
    """User-drawn annotations on charts (trendlines, fib, zones, etc.)."""

    TOOL_CHOICES = [
        ("trendline", "Trendline"),
        ("horizontal", "Horizontal Line"),
        ("fibonacci", "Fibonacci Retracement"),
        ("rectangle", "Rectangle Zone"),
        ("ray", "Ray"),
        ("pitchfork", "Pitchfork"),
        ("text", "Text Label"),
        ("pricerange", "Price Range"),
    ]

    pair = models.CharField(max_length=10, db_index=True)
    timeframe = models.CharField(max_length=5)
    tool_type = models.CharField(max_length=20, choices=TOOL_CHOICES)
    coordinates = models.JSONField()  # [{time, price}, ...]
    color = models.CharField(max_length=20, default="#2196F3")
    thickness = models.IntegerField(default=2)
    label = models.CharField(max_length=100, blank=True)
    visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tool_type} on {self.pair} {self.timeframe}"


class PatternTemplate(models.Model):
    """Saved price pattern templates for similarity matching."""

    name = models.CharField(max_length=100)
    pair = models.CharField(max_length=10)
    timeframe = models.CharField(max_length=5)
    price_sequence = models.JSONField()  # Normalized [0-1] price values
    lookback_candles = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.pair} {self.timeframe}, {self.lookback_candles} candles)"


class PatternOccurrence(models.Model):
    """Historical occurrence of a saved pattern."""

    template = models.ForeignKey(
        PatternTemplate, on_delete=models.CASCADE, related_name="occurrences"
    )
    found_at = models.DateTimeField()
    similarity_score = models.FloatField()
    outcome_pips = models.FloatField()  # Price move after pattern completed
    outcome_direction = models.CharField(max_length=10)  # bullish / bearish / flat

    class Meta:
        ordering = ["-found_at"]

    def __str__(self):
        return f"{self.template.name} match ({self.similarity_score:.0%}) → {self.outcome_pips:.1f} pips"


class NewsEvent(models.Model):
    """Economic calendar events cached from MT5."""

    IMPACT_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
    ]

    currency = models.CharField(max_length=5)
    event_name = models.CharField(max_length=200)
    time = models.DateTimeField(db_index=True)
    importance = models.CharField(max_length=10, choices=IMPACT_CHOICES)
    actual = models.CharField(max_length=50, blank=True)
    forecast = models.CharField(max_length=50, blank=True)
    previous = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["time"]

    def __str__(self):
        return f"{self.currency} {self.event_name} ({self.importance})"


class Alert(models.Model):
    """Triggered alerts for the notification system."""

    TYPE_CHOICES = [
        ("trade_score", "Trade Score Threshold"),
        ("pattern_match", "Pattern Match"),
        ("news_warning", "News Warning"),
        ("price_level", "Price Level Hit"),
        ("mt5_disconnect", "MT5 Disconnected"),
    ]

    alert_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    pair = models.CharField(max_length=10, blank=True)
    message = models.TextField()
    triggered_at = models.DateTimeField(auto_now_add=True)
    acknowledged = models.BooleanField(default=False)

    class Meta:
        ordering = ["-triggered_at"]

    def __str__(self):
        return f"{self.alert_type}: {self.message[:50]}"


class UserSettings(models.Model):
    """User preferences and configuration."""

    default_risk_pct = models.FloatField(default=1.0)
    default_pairs = models.JSONField(
        default=list,
        blank=True,
    )
    score_weights = models.JSONField(
        default=dict,
        blank=True,
    )
    swing_lookback = models.IntegerField(default=5)
    alert_sound = models.BooleanField(default=True)
    alert_browser = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "User settings"

    def __str__(self):
        return "User Settings"
