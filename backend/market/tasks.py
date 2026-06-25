"""
Celery tasks — background polling of MT5 and indicator computation.
Pushes updates to connected WebSocket clients via Django Channels.
"""

import json
import logging

import pandas as pd
import redis
from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer

from .services import mt5_service
from .services.indicators import (
    compute_all_indicators,
    compute_trade_score,
    detect_bos,
    detect_choch,
    detect_equal_highs,
    detect_equal_lows,
    find_sr_zones,
    find_swing_highs,
    find_swing_lows,
    get_session_info,
    get_support_resistance,
    live_pattern_scan,
    trend_score,
)
from .services.risk_calculator import get_pip_size

logger = logging.getLogger(__name__)
redis_client = redis.Redis(host="127.0.0.1", port=6379, db=1, decode_responses=True)

# Track MT5 connection state
_mt5_initialized = False


def _ensure_mt5():
    """Ensure MT5 is connected, attempt reconnect if not."""
    global _mt5_initialized
    if not _mt5_initialized or not mt5_service.is_connected():
        _mt5_initialized = mt5_service.initialize()
        if not _mt5_initialized:
            logger.warning("MT5 not connected — skipping task")
            _push_alert("mt5_disconnect", "", "MT5 terminal disconnected")
    return _mt5_initialized


def _push_to_ws(group_name, data):
    """Push data to a WebSocket group via Channels."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                group_name,
                {"type": "market.update", "data": data},
            )
    except Exception as e:
        logger.error("WebSocket push failed for %s: %s", group_name, e)


def _push_alert(alert_type, pair, message):
    """Push an alert to the alerts WebSocket group."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "alerts",
                {
                    "type": "alert.message",
                    "data": {
                        "alert_type": alert_type,
                        "pair": pair,
                        "message": message,
                    },
                },
            )
    except Exception as e:
        logger.error("Alert push failed: %s", e)

    # Also persist alert to DB
    try:
        from .models import Alert
        Alert.objects.create(alert_type=alert_type, pair=pair, message=message)
    except Exception:
        pass


@shared_task(name="market.tasks.poll_mt5_ticks")
def poll_mt5_ticks():
    """Poll MT5 for latest tick prices and push to WebSocket clients."""
    if not _ensure_mt5():
        return

    ticks = mt5_service.get_ticks_batch()
    if not ticks:
        return

    # Cache in Redis
    redis_client.set("latest_ticks", json.dumps(ticks), ex=10)

    # Push each pair's tick to its WebSocket group
    for symbol, tick_data in ticks.items():
        group = f"pair_{symbol.lower()}"
        _push_to_ws(group, {"type": "tick", **tick_data})

    # Also push all ticks to the overview group
    _push_to_ws("market_overview", {"type": "ticks", "data": ticks})


@shared_task(name="market.tasks.poll_mt5_candles")
def poll_mt5_candles():
    """Poll MT5 for latest candles across all pairs and timeframes."""
    if not _ensure_mt5():
        return

    pairs = mt5_service.DEFAULT_PAIRS
    timeframes = ["M1", "M5", "M15", "H1", "H4", "D1", "W1"]

    for pair in pairs:
        for tf in timeframes:
            try:
                candles = mt5_service.get_candles(pair, tf, count=500)
                if candles:
                    cache_key = f"candles:{pair}:{tf}"
                    redis_client.set(cache_key, json.dumps(candles, default=str), ex=120)
            except Exception as e:
                logger.error("Candle fetch failed for %s %s: %s", pair, tf, e)


@shared_task(name="market.tasks.compute_indicators")
def compute_indicators():
    """
    Compute technical indicators for all cached candle data and push analysis.
    Reads from Redis cache — does NOT require MT5 to be connected.
    """
    pairs = mt5_service.DEFAULT_PAIRS
    session_info = get_session_info()

    for pair in pairs:
        try:
            _compute_pair_analysis(pair, session_info)
        except Exception as e:
            logger.error("Indicator computation failed for %s: %s", pair, e)


def _compute_pair_analysis(pair, session_info):
    """Compute full analysis for a single pair."""
    analysis = {"pair": pair, "session": session_info}
    timeframe_data = {}
    pip_size = get_pip_size(pair)

    for tf in ["M5", "M15", "H1", "H4", "D1"]:
        cache_key = f"candles:{pair}:{tf}"
        raw = redis_client.get(cache_key)
        if not raw:
            continue

        try:
            candles = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Corrupt cache for %s:%s", pair, tf)
            continue

        if not candles or len(candles) < 5:
            continue

        df = pd.DataFrame(candles)
        df["time"] = pd.to_datetime(df["time"])
        df = compute_all_indicators(df)

        score, direction = trend_score(df)
        tf_data = {
            "trend_score": score,
            "trend_direction": direction,
        }

        # Safely extract latest indicator values
        for col in ["ema_20", "ema_50", "ema_200", "rsi", "adx"]:
            if col in df.columns and not pd.isna(df[col].iloc[-1]):
                tf_data[col] = round(float(df[col].iloc[-1]), 5)
            else:
                tf_data[col] = None

        timeframe_data[tf] = tf_data

        # Structure + liquidity detection on H1
        if tf == "H1" and len(df) > 20:
            swing_highs = find_swing_highs(df, lookback=5)
            swing_lows = find_swing_lows(df, lookback=5)
            current_price = float(df["close"].iloc[-1])

            bos = detect_bos(swing_highs, swing_lows, current_price)
            choch = detect_choch(swing_highs, swing_lows)
            eq_highs = detect_equal_highs(swing_highs, pip_size=pip_size)
            eq_lows = detect_equal_lows(swing_lows, pip_size=pip_size)
            sr_zones = find_sr_zones(swing_highs, swing_lows, pip_size=pip_size)

            analysis["structure"] = {
                "bos": bos,
                "choch": choch,
                "swing_highs": swing_highs[-5:] if swing_highs else [],
                "swing_lows": swing_lows[-5:] if swing_lows else [],
            }
            analysis["liquidity"] = {
                "equal_highs": eq_highs,
                "equal_lows": eq_lows,
            }
            analysis["sr_zones"] = sr_zones

            # Compute trade quality score
            h4_data = timeframe_data.get("H4", {})
            h1_data = timeframe_data.get("H1", {})
            rsi_val = h1_data.get("rsi")
            at_zone = any(
                abs(current_price - z["low"]) < 10 * pip_size
                or abs(current_price - z["high"]) < 10 * pip_size
                for z in sr_zones
            ) if sr_zones else False

            score_input = {
                "trend_aligned": (
                    h4_data.get("trend_direction") == h1_data.get("trend_direction")
                    and h1_data.get("trend_direction") != "neutral"
                ),
                "bos_detected": bos is not None,
                "at_sr_zone": at_zone,
                "liquidity_swept": len(eq_highs) > 0 or len(eq_lows) > 0,
                "rsi_ok": rsi_val is not None and 30 < rsi_val < 70,
                "volume_above_avg": False,  # TODO: add volume check
                "session_active": len(session_info.get("active_sessions", [])) > 0,
                "no_high_impact_news": True,  # Updated by news check
            }
            analysis["trade_score"] = compute_trade_score(score_input)
            analysis["score_breakdown"] = score_input

    # S/R from D1 and W1
    d1_raw = redis_client.get(f"candles:{pair}:D1")
    w1_raw = redis_client.get(f"candles:{pair}:W1")
    if d1_raw and w1_raw:
        try:
            d1_df = pd.DataFrame(json.loads(d1_raw))
            w1_df = pd.DataFrame(json.loads(w1_raw))
            analysis["key_levels"] = get_support_resistance(d1_df, w1_df)
        except Exception:
            pass

    analysis["timeframes"] = timeframe_data

    # Cache the full analysis
    redis_client.set(f"analysis:{pair}", json.dumps(analysis, default=str), ex=30)

    # Push to WebSocket
    group = f"pair_{pair.lower()}"
    _push_to_ws(group, {"type": "analysis", **analysis})


@shared_task(name="market.tasks.scan_patterns")
def scan_patterns():
    """
    Scan current price data against saved pattern templates.
    Pushes matches to WebSocket for live overlay display.
    """
    from .models import PatternTemplate

    templates = PatternTemplate.objects.all()
    if not templates.exists():
        return

    for tmpl in templates:
        cache_key = f"candles:{tmpl.pair}:{tmpl.timeframe}"
        raw = redis_client.get(cache_key)
        if not raw:
            continue

        try:
            candles = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue

        if len(candles) < tmpl.lookback_candles:
            continue

        closes = [c["close"] for c in candles]

        # Run live pattern scan
        template_data = [{
            "id": tmpl.id,
            "name": tmpl.name,
            "sequence": tmpl.price_sequence,
        }]
        matches = live_pattern_scan(closes, template_data, min_match_ratio=0.6, threshold=0.85)

        if matches:
            # Push pattern match to the pair's WebSocket group
            group = f"pair_{tmpl.pair.lower()}"
            _push_to_ws(group, {
                "type": "pattern_match",
                "pair": tmpl.pair,
                "timeframe": tmpl.timeframe,
                "matches": matches,
            })

            # Alert if high similarity
            for m in matches:
                if m["similarity"] >= 0.90 and m["completion"] >= 0.7:
                    _push_alert(
                        "pattern_match",
                        tmpl.pair,
                        f"Pattern '{tmpl.name}' {int(m['completion'] * 100)}% formed "
                        f"({int(m['similarity'] * 100)}% similar) on {tmpl.pair} {tmpl.timeframe}",
                    )
