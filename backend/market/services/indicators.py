"""
Technical indicator calculations using pandas-ta.
Computes EMA, RSI, ADX, trend scores, support/resistance, and swing points.
"""

import numpy as np
import pandas as pd
import pandas_ta as ta


def compute_ema(df, periods=(20, 50, 200)):
    """Add EMA columns to dataframe."""
    for p in periods:
        if len(df) >= p:
            df[f"ema_{p}"] = ta.ema(df["close"], length=p)
    return df


def compute_rsi(df, period=14):
    """Add RSI column."""
    if len(df) >= period:
        df["rsi"] = ta.rsi(df["close"], length=period)
    return df


def compute_adx(df, period=14):
    """Add ADX column."""
    if len(df) >= period:
        adx_df = ta.adx(df["high"], df["low"], df["close"], length=period)
        if adx_df is not None:
            df["adx"] = adx_df.iloc[:, 0]  # ADX column
    return df


def compute_all_indicators(df):
    """Compute all standard indicators on a candle dataframe."""
    df = compute_ema(df)
    df = compute_rsi(df)
    df = compute_adx(df)
    return df


def trend_score(df):
    """
    Calculate trend score (0-100) based on EMA alignment + ADX.
    Higher score = stronger trend.
    """
    if len(df) < 200:
        return 0, "neutral"

    row = df.iloc[-1]
    ema20 = row.get("ema_20")
    ema50 = row.get("ema_50")
    ema200 = row.get("ema_200")
    adx = row.get("adx")

    if any(pd.isna(v) for v in [ema20, ema50, ema200]):
        return 0, "neutral"

    score = 0

    # Bullish alignment
    if ema20 > ema50:
        score += 25
    elif ema20 < ema50:
        score -= 25

    if ema50 > ema200:
        score += 25
    elif ema50 < ema200:
        score -= 25

    if ema20 > ema200:
        score += 15
    elif ema20 < ema200:
        score -= 15

    # ADX strength
    if adx is not None and not pd.isna(adx):
        if adx > 20:
            score += 15 if score > 0 else -15
        if adx > 30:
            score += 10 if score > 0 else -10
        if adx > 40:
            score += 10 if score > 0 else -10

    # Normalize to 0-100
    # Raw range: -100 to +100 → map to 0-100
    normalized = int((score + 100) / 2)
    normalized = max(0, min(100, normalized))

    if normalized >= 70:
        direction = "bullish"
    elif normalized <= 30:
        direction = "bearish"
    else:
        direction = "neutral"

    return normalized, direction


def find_swing_highs(df, lookback=5):
    """Find fractal swing highs: high is the highest in lookback candles on both sides."""
    highs = []
    for i in range(lookback, len(df) - lookback):
        window = df["high"].iloc[i - lookback : i + lookback + 1]
        if df["high"].iloc[i] == window.max():
            highs.append({
                "index": i,
                "price": float(df["high"].iloc[i]),
                "time": df["time"].iloc[i].isoformat() if hasattr(df["time"].iloc[i], "isoformat") else str(df["time"].iloc[i]),
            })
    return highs


def find_swing_lows(df, lookback=5):
    """Find fractal swing lows: low is the lowest in lookback candles on both sides."""
    lows = []
    for i in range(lookback, len(df) - lookback):
        window = df["low"].iloc[i - lookback : i + lookback + 1]
        if df["low"].iloc[i] == window.min():
            lows.append({
                "index": i,
                "price": float(df["low"].iloc[i]),
                "time": df["time"].iloc[i].isoformat() if hasattr(df["time"].iloc[i], "isoformat") else str(df["time"].iloc[i]),
            })
    return lows


def detect_bos(swing_highs, swing_lows, current_price):
    """
    Detect Break of Structure.
    BOS = price breaks above last swing high (bullish) or below last swing low (bearish).
    """
    result = None
    if swing_highs and current_price > swing_highs[-1]["price"]:
        result = {"type": "bullish_bos", "level": swing_highs[-1]["price"], "time": swing_highs[-1]["time"]}
    elif swing_lows and current_price < swing_lows[-1]["price"]:
        result = {"type": "bearish_bos", "level": swing_lows[-1]["price"], "time": swing_lows[-1]["time"]}
    return result


def detect_choch(swing_highs, swing_lows):
    """
    Detect Change of Character.
    In an uptrend (higher lows), a lower low = bearish CHOCH.
    In a downtrend (lower highs), a higher high = bullish CHOCH.
    """
    # Check swing lows for bearish CHOCH
    if len(swing_lows) >= 3:
        prev = swing_lows[-2]["price"]
        before_prev = swing_lows[-3]["price"]
        current = swing_lows[-1]["price"]
        # Was making higher lows, now lower low
        if before_prev < prev and current < prev:
            return {
                "type": "bearish_choch",
                "level": current,
                "time": swing_lows[-1]["time"],
            }

    # Check swing highs for bullish CHOCH
    if len(swing_highs) >= 3:
        prev = swing_highs[-2]["price"]
        before_prev = swing_highs[-3]["price"]
        current = swing_highs[-1]["price"]
        # Was making lower highs, now higher high
        if before_prev > prev and current > prev:
            return {
                "type": "bullish_choch",
                "level": current,
                "time": swing_highs[-1]["time"],
            }

    return None


def get_support_resistance(df_d1, df_w1):
    """
    Calculate key S/R levels: PDH, PDL, PWH, PWL, and daily open.
    """
    levels = {}
    if len(df_d1) >= 2:
        levels["PDH"] = float(df_d1["high"].iloc[-2])
        levels["PDL"] = float(df_d1["low"].iloc[-2])
        levels["DO"] = float(df_d1["open"].iloc[-1])
    if len(df_w1) >= 2:
        levels["PWH"] = float(df_w1["high"].iloc[-2])
        levels["PWL"] = float(df_w1["low"].iloc[-2])
    return levels


def find_sr_zones(swing_highs, swing_lows, tolerance_pips=5, pip_size=0.0001):
    """
    Cluster nearby swing points into support/resistance zones.
    """
    all_levels = (
        [{"price": h["price"], "type": "resistance"} for h in swing_highs]
        + [{"price": l["price"], "type": "support"} for l in swing_lows]
    )
    all_levels.sort(key=lambda x: x["price"])

    zones = []
    used = set()
    tolerance = tolerance_pips * pip_size

    for i, level in enumerate(all_levels):
        if i in used:
            continue
        cluster = [level]
        used.add(i)
        for j in range(i + 1, len(all_levels)):
            if j in used:
                continue
            if abs(all_levels[j]["price"] - level["price"]) <= tolerance:
                cluster.append(all_levels[j])
                used.add(j)

        if len(cluster) >= 2:
            prices = [c["price"] for c in cluster]
            zone_type = max(set(c["type"] for c in cluster), key=lambda t: sum(1 for c in cluster if c["type"] == t))
            zones.append({
                "type": zone_type,
                "low": min(prices),
                "high": max(prices),
                "touches": len(cluster),
            })

    return zones


def detect_equal_highs(swing_highs, tolerance_pips=3, pip_size=0.0001):
    """Find equal highs (liquidity pools above)."""
    clusters = []
    tolerance = tolerance_pips * pip_size
    used = set()

    for i, h1 in enumerate(swing_highs):
        if i in used:
            continue
        group = [h1]
        used.add(i)
        for j, h2 in enumerate(swing_highs):
            if j <= i or j in used:
                continue
            if abs(h1["price"] - h2["price"]) <= tolerance:
                group.append(h2)
                used.add(j)
        if len(group) >= 2:
            clusters.append({
                "level": max(h["price"] for h in group),
                "type": "equal_highs",
                "count": len(group),
            })
    return clusters


def detect_equal_lows(swing_lows, tolerance_pips=3, pip_size=0.0001):
    """Find equal lows (liquidity pools below)."""
    clusters = []
    tolerance = tolerance_pips * pip_size
    used = set()

    for i, l1 in enumerate(swing_lows):
        if i in used:
            continue
        group = [l1]
        used.add(i)
        for j, l2 in enumerate(swing_lows):
            if j <= i or j in used:
                continue
            if abs(l1["price"] - l2["price"]) <= tolerance:
                group.append(l2)
                used.add(j)
        if len(group) >= 2:
            clusters.append({
                "level": min(l["price"] for l in group),
                "type": "equal_lows",
                "count": len(group),
            })
    return clusters


def compute_trade_score(analysis):
    """
    Compute trade quality score (0-100) based on multiple conditions.
    Uses default weights; user can customize later.
    """
    weights = {
        "trend_aligned": 20,
        "structure_confirmed": 15,
        "at_sr_zone": 15,
        "liquidity_swept": 10,
        "rsi_confirmation": 10,
        "volume_above_avg": 10,
        "session_active": 10,
        "no_news": 10,
    }

    score = 0

    if analysis.get("trend_aligned"):
        score += weights["trend_aligned"]
    if analysis.get("bos_detected"):
        score += weights["structure_confirmed"]
    if analysis.get("at_sr_zone"):
        score += weights["at_sr_zone"]
    if analysis.get("liquidity_swept"):
        score += weights["liquidity_swept"]
    if analysis.get("rsi_ok"):
        score += weights["rsi_confirmation"]
    if analysis.get("volume_above_avg"):
        score += weights["volume_above_avg"]
    if analysis.get("session_active"):
        score += weights["session_active"]
    if analysis.get("no_high_impact_news"):
        score += weights["no_news"]

    return score


def get_session_info():
    """Determine current trading session based on UTC time."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    hour = now.hour

    sessions = {
        "Sydney": (21, 6),
        "Tokyo": (0, 9),
        "London": (7, 16),
        "New York": (12, 21),
    }

    active = []
    for name, (start, end) in sessions.items():
        if start <= end:
            if start <= hour < end:
                active.append(name)
        else:  # wraps midnight
            if hour >= start or hour < end:
                active.append(name)

    is_overlap = len(active) >= 2
    volatility = "HIGH" if is_overlap or "London" in active or "New York" in active else "MEDIUM" if "Tokyo" in active else "LOW"

    return {
        "active_sessions": active,
        "is_overlap": is_overlap,
        "volatility": volatility,
        "current_hour_utc": hour,
    }


def normalize_pattern(prices):
    """Convert absolute prices to 0-1 range for pattern comparison."""
    min_p, max_p = min(prices), max(prices)
    if max_p == min_p:
        return [0.5] * len(prices)
    return [(p - min_p) / (max_p - min_p) for p in prices]


def find_similar_patterns(template_seq, historical_closes, window_size, threshold=0.85, pip_size=0.0001):
    """
    Slide window across historical close prices, compare normalized shapes.
    Returns list of matches with similarity and outcome.
    """
    template_norm = normalize_pattern(template_seq)
    matches = []

    for i in range(len(historical_closes) - window_size - 50):
        window = historical_closes[i : i + window_size]
        window_norm = normalize_pattern(window)

        # RMSE similarity
        rmse = np.sqrt(np.mean((np.array(template_norm) - np.array(window_norm)) ** 2))
        similarity = 1 - rmse

        if similarity >= threshold:
            # Outcome: what happened 50 candles after pattern completed
            future_price = historical_closes[min(i + window_size + 50, len(historical_closes) - 1)]
            end_price = historical_closes[i + window_size]
            outcome_pips = (future_price - end_price) / pip_size

            matches.append({
                "index": i,
                "similarity": round(similarity, 4),
                "outcome_pips": round(outcome_pips, 1),
                "direction": "bullish" if outcome_pips > 20 else "bearish" if outcome_pips < -20 else "flat",
            })

    return matches


def live_pattern_scan(current_closes, template_sequences, min_match_ratio=0.6, threshold=0.85):
    """
    Scan current chart against saved pattern templates.
    Returns partial matches (60%+ formed) for live overlay.
    """
    results = []

    for tmpl in template_sequences:
        pattern_len = len(tmpl["sequence"])
        template_norm = normalize_pattern(tmpl["sequence"])

        for partial_len in range(int(pattern_len * min_match_ratio), min(pattern_len + 1, len(current_closes) + 1)):
            if partial_len > len(current_closes):
                continue

            recent = current_closes[-partial_len:]
            recent_norm = normalize_pattern(recent)
            template_partial = template_norm[:partial_len]

            rmse = np.sqrt(np.mean((np.array(template_partial) - np.array(recent_norm)) ** 2))
            similarity = 1 - rmse

            if similarity >= threshold:
                results.append({
                    "template_id": tmpl["id"],
                    "template_name": tmpl["name"],
                    "similarity": round(similarity, 4),
                    "matched_candles": partial_len,
                    "total_candles": pattern_len,
                    "completion": round(partial_len / pattern_len, 2),
                    "remaining_pattern": tmpl["sequence"][partial_len:],
                    "full_pattern": tmpl["sequence"],
                })
                break  # Best partial match for this template

    return results
