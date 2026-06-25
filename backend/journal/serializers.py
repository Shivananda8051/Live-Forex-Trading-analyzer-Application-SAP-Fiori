from rest_framework import serializers

from .models import Trade


class TradeSerializer(serializers.ModelSerializer):
    risk_reward = serializers.ReadOnlyField()
    sl_pips = serializers.ReadOnlyField()
    tp_pips = serializers.ReadOnlyField()

    class Meta:
        model = Trade
        fields = "__all__"


class TradeAnalyticsSerializer(serializers.Serializer):
    """Read-only analytics summary."""

    total_trades = serializers.IntegerField()
    wins = serializers.IntegerField()
    losses = serializers.IntegerField()
    breakeven = serializers.IntegerField()
    win_rate = serializers.FloatField()
    avg_rr = serializers.FloatField()
    profit_factor = serializers.FloatField()
    total_pnl = serializers.FloatField()
    best_pair = serializers.CharField()
    worst_pair = serializers.CharField()
    best_session = serializers.CharField()
    avg_trade_score = serializers.FloatField()
    max_consecutive_wins = serializers.IntegerField()
    max_consecutive_losses = serializers.IntegerField()
