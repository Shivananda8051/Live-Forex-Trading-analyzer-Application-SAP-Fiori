from django.db import models


class Trade(models.Model):
    """Trade journal entry — manual or auto-imported from MT5."""

    DIRECTION_CHOICES = [("BUY", "Buy"), ("SELL", "Sell")]
    RESULT_CHOICES = [
        ("WIN", "Win"),
        ("LOSS", "Loss"),
        ("BE", "Breakeven"),
        ("OPEN", "Open"),
    ]

    pair = models.CharField(max_length=10, db_index=True)
    direction = models.CharField(max_length=4, choices=DIRECTION_CHOICES)
    entry_price = models.FloatField()
    sl_price = models.FloatField()
    tp_price = models.FloatField()
    lot_size = models.FloatField()
    result = models.CharField(max_length=4, choices=RESULT_CHOICES, default="OPEN")
    pnl = models.FloatField(null=True, blank=True)
    screenshot = models.ImageField(upload_to="trade_screenshots/", null=True, blank=True)
    notes = models.TextField(blank=True)

    # Auto-captured context at time of trade
    trade_score = models.IntegerField(null=True, blank=True)
    session = models.CharField(max_length=20, blank=True)
    trend_direction = models.CharField(max_length=10, blank=True)

    # MT5 reference
    mt5_ticket = models.BigIntegerField(null=True, blank=True, unique=True)

    # Drawing references
    drawings = models.ManyToManyField(
        "market.ChartDrawing", blank=True, related_name="trades"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.direction} {self.pair} @ {self.entry_price} → {self.result}"

    @property
    def risk_reward(self):
        if not self.sl_price or not self.tp_price or not self.entry_price:
            return None
        sl_dist = abs(self.entry_price - self.sl_price)
        tp_dist = abs(self.tp_price - self.entry_price)
        if sl_dist == 0:
            return None
        return round(tp_dist / sl_dist, 2)

    @property
    def sl_pips(self):
        pip_size = 0.01 if "JPY" in self.pair else 0.0001
        return round(abs(self.entry_price - self.sl_price) / pip_size, 1)

    @property
    def tp_pips(self):
        pip_size = 0.01 if "JPY" in self.pair else 0.0001
        return round(abs(self.tp_price - self.entry_price) / pip_size, 1)
