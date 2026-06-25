import json

import redis
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import (
    Alert,
    ChartDrawing,
    NewsEvent,
    PatternOccurrence,
    PatternTemplate,
    UserSettings,
)
from .serializers import (
    AlertSerializer,
    ChartDrawingSerializer,
    NewsEventSerializer,
    PatternOccurrenceSerializer,
    PatternTemplateSerializer,
    RiskCalculatorSerializer,
    UserSettingsSerializer,
)
from .services import mt5_service
from .services.indicators import (
    find_similar_patterns,
    get_session_info,
    normalize_pattern,
)
from .services.risk_calculator import calculate_position, get_pip_size

redis_client = redis.Redis(host="127.0.0.1", port=6379, db=1, decode_responses=True)


# --- Market Data Endpoints ---


@api_view(["GET"])
def candles(request):
    """
    GET /api/market/candles/?pair=EURUSD&timeframe=H1&count=300
    Returns cached candle data from Redis (populated by Celery tasks).
    Falls back to direct MT5 fetch if cache is empty.
    """
    pair = request.query_params.get("pair", "EURUSD")
    timeframe = request.query_params.get("timeframe", "H1")
    count = int(request.query_params.get("count", 300))

    cache_key = f"candles:{pair}:{timeframe}"
    raw = redis_client.get(cache_key)

    if raw:
        data = json.loads(raw)[:count]
        return Response(data)

    # Fallback: direct MT5 fetch
    data = mt5_service.get_candles(pair, timeframe, count)
    if data:
        return Response(data)
    return Response({"error": "No data available"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(["GET"])
def analysis(request):
    """
    GET /api/market/analysis/?pair=EURUSD
    Returns cached analysis (indicators, structure, liquidity) from Redis.
    """
    pair = request.query_params.get("pair", "EURUSD")
    raw = redis_client.get(f"analysis:{pair}")

    if raw:
        return Response(json.loads(raw))
    return Response({"error": "Analysis not available yet"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(["GET"])
def ticks(request):
    """
    GET /api/market/ticks/
    Returns latest tick prices for all pairs.
    """
    raw = redis_client.get("latest_ticks")
    if raw:
        return Response(json.loads(raw))
    return Response({})


@api_view(["GET"])
def account_info(request):
    """GET /api/market/account/ — MT5 account details."""
    info = mt5_service.get_account_info()
    if info:
        return Response(info)
    return Response({"error": "MT5 not connected"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(["GET"])
def session_info(request):
    """GET /api/market/session/ — Current trading session info."""
    return Response(get_session_info())


@api_view(["GET"])
def news_events(request):
    """GET /api/market/news/ — Upcoming economic calendar events."""
    events = mt5_service.get_news_events()
    return Response(events)


@api_view(["POST"])
def risk_calculate(request):
    """POST /api/market/risk/ — Calculate position size."""
    serializer = RiskCalculatorSerializer(data=request.data)
    if serializer.is_valid():
        result = calculate_position(**serializer.validated_data)
        return Response(result)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --- CRUD ViewSets ---


class ChartDrawingViewSet(viewsets.ModelViewSet):
    """CRUD for chart drawings. Filter by pair and timeframe."""

    serializer_class = ChartDrawingSerializer
    queryset = ChartDrawing.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        pair = self.request.query_params.get("pair")
        timeframe = self.request.query_params.get("timeframe")
        if pair:
            qs = qs.filter(pair=pair)
        if timeframe:
            qs = qs.filter(timeframe=timeframe)
        return qs


class PatternTemplateViewSet(viewsets.ModelViewSet):
    """CRUD for pattern templates + pattern matching endpoint."""

    serializer_class = PatternTemplateSerializer
    queryset = PatternTemplate.objects.all()

    @action(detail=True, methods=["post"])
    def find_matches(self, request, pk=None):
        """
        POST /api/market/patterns/<id>/find_matches/
        Search historical data for similar patterns.
        """
        template = self.get_object()
        pair = request.data.get("pair", template.pair)
        timeframe = request.data.get("timeframe", template.timeframe)
        threshold = float(request.data.get("threshold", 0.85))

        # Get historical candle data
        cache_key = f"candles:{pair}:{timeframe}"
        raw = redis_client.get(cache_key)
        if not raw:
            return Response({"error": "No candle data cached"}, status=status.HTTP_404_NOT_FOUND)

        candles_data = json.loads(raw)
        closes = [c["close"] for c in candles_data]
        pip_size = get_pip_size(pair)

        matches = find_similar_patterns(
            template.price_sequence, closes, template.lookback_candles, threshold, pip_size
        )

        # Store occurrences
        for m in matches:
            PatternOccurrence.objects.get_or_create(
                template=template,
                found_at=candles_data[m["index"]]["time"],
                defaults={
                    "similarity_score": m["similarity"],
                    "outcome_pips": m["outcome_pips"],
                    "outcome_direction": m["direction"],
                },
            )

        # Summary stats
        bullish = sum(1 for m in matches if m["direction"] == "bullish")
        bearish = sum(1 for m in matches if m["direction"] == "bearish")
        flat = sum(1 for m in matches if m["direction"] == "flat")

        return Response({
            "template": template.name,
            "total_matches": len(matches),
            "threshold": threshold,
            "outcomes": {"bullish": bullish, "bearish": bearish, "flat": flat},
            "avg_outcome_pips": round(sum(m["outcome_pips"] for m in matches) / max(len(matches), 1), 1),
            "matches": matches[:20],  # Top 20
        })


class AlertViewSet(viewsets.ModelViewSet):
    serializer_class = AlertSerializer
    queryset = Alert.objects.all()

    @action(detail=False, methods=["post"])
    def acknowledge_all(self, request):
        Alert.objects.filter(acknowledged=False).update(acknowledged=True)
        return Response({"status": "ok"})


@api_view(["GET", "PUT"])
def user_settings(request):
    """GET/PUT /api/market/settings/ — User preferences."""
    obj, _ = UserSettings.objects.get_or_create(pk=1)
    if request.method == "GET":
        return Response(UserSettingsSerializer(obj).data)
    serializer = UserSettingsSerializer(obj, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
