from rest_framework import serializers

from .models import (
    Alert,
    CandleData,
    ChartDrawing,
    NewsEvent,
    PatternOccurrence,
    PatternTemplate,
    UserSettings,
)


class CandleDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandleData
        fields = "__all__"


class ChartDrawingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChartDrawing
        fields = "__all__"


class PatternTemplateSerializer(serializers.ModelSerializer):
    occurrences_count = serializers.SerializerMethodField()

    class Meta:
        model = PatternTemplate
        fields = "__all__"

    def get_occurrences_count(self, obj):
        return obj.occurrences.count()


class PatternOccurrenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatternOccurrence
        fields = "__all__"


class NewsEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsEvent
        fields = "__all__"


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = "__all__"


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = "__all__"


class RiskCalculatorSerializer(serializers.Serializer):
    balance = serializers.FloatField()
    risk_pct = serializers.FloatField(default=1.0)
    sl_pips = serializers.FloatField()
    pair = serializers.CharField(max_length=10)
