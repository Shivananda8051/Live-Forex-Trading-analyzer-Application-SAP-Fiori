"""
MetaTrader 5 connection service.
Handles connecting to the MT5 terminal, fetching ticks, candles, account info,
trade history, and economic calendar.
"""

import logging
from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5
import pandas as pd
from django.conf import settings

logger = logging.getLogger(__name__)

# MT5 timeframe mapping
TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
}

# Default pairs to track
DEFAULT_PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF",
    "AUDUSD", "USDCAD", "NZDUSD", "GBPJPY",
    "EURJPY", "XAUUSD",
]


def initialize():
    """Connect to the MT5 terminal. Returns True on success."""
    kwargs = {}
    if settings.MT5_PATH:
        kwargs["path"] = settings.MT5_PATH
    if settings.MT5_ACCOUNT:
        kwargs["login"] = int(settings.MT5_ACCOUNT)
    if settings.MT5_PASSWORD:
        kwargs["password"] = settings.MT5_PASSWORD
    if settings.MT5_SERVER:
        kwargs["server"] = settings.MT5_SERVER

    if not mt5.initialize(**kwargs):
        error = mt5.last_error()
        logger.error("MT5 initialize failed: %s", error)
        return False

    info = mt5.terminal_info()
    logger.info("MT5 connected: %s (build %s)", info.name, info.build)
    return True


def shutdown():
    """Disconnect from MT5."""
    mt5.shutdown()


def is_connected():
    """Check if MT5 terminal is responsive."""
    info = mt5.terminal_info()
    return info is not None and info.connected


def get_tick(symbol):
    """Get latest tick (bid/ask) for a symbol."""
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None
    return {
        "symbol": symbol,
        "bid": tick.bid,
        "ask": tick.ask,
        "spread": round((tick.ask - tick.bid) / _pip_size(symbol), 1),
        "time": datetime.fromtimestamp(tick.time, tz=timezone.utc).isoformat(),
    }


def get_ticks_batch(symbols=None):
    """Get latest ticks for multiple symbols."""
    symbols = symbols or DEFAULT_PAIRS
    ticks = {}
    for symbol in symbols:
        tick = get_tick(symbol)
        if tick:
            ticks[symbol] = tick
    return ticks


def get_candles(symbol, timeframe="H1", count=500):
    """
    Fetch OHLCV candles from MT5.
    Returns a list of dicts with: time, open, high, low, close, volume.
    """
    tf = TIMEFRAME_MAP.get(timeframe)
    if tf is None:
        logger.error("Unknown timeframe: %s", timeframe)
        return []

    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if rates is None or len(rates) == 0:
        logger.warning("No candle data for %s %s", symbol, timeframe)
        return []

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.rename(columns={"tick_volume": "volume"})
    return df[["time", "open", "high", "low", "close", "volume"]].to_dict("records")


def get_account_info():
    """Get MT5 account details (balance, equity, margin)."""
    info = mt5.account_info()
    if info is None:
        return None
    return {
        "balance": info.balance,
        "equity": info.equity,
        "margin": info.margin,
        "free_margin": info.margin_free,
        "leverage": info.leverage,
        "currency": info.currency,
        "profit": info.profit,
    }


def get_trade_history(days=30):
    """Get closed trades from MT5 for the last N days."""
    date_from = datetime.now(timezone.utc) - timedelta(days=days)
    date_to = datetime.now(timezone.utc)
    deals = mt5.history_deals_get(date_from, date_to)
    if deals is None:
        return []
    return [
        {
            "ticket": d.ticket,
            "order": d.order,
            "symbol": d.symbol,
            "type": "BUY" if d.type == 0 else "SELL",
            "volume": d.volume,
            "price": d.price,
            "profit": d.profit,
            "commission": d.commission,
            "swap": d.swap,
            "time": datetime.fromtimestamp(d.time, tz=timezone.utc).isoformat(),
        }
        for d in deals
    ]


def get_news_events(hours_ahead=24):
    """Get upcoming economic calendar events from MT5."""
    now = datetime.now(timezone.utc)
    end = now + timedelta(hours=hours_ahead)
    try:
        events = mt5.calendar_get(now, end)
    except Exception:
        logger.warning("MT5 calendar_get not available on this build")
        return []

    if events is None:
        return []

    result = []
    for e in events:
        importance_map = {0: "LOW", 1: "MEDIUM", 2: "HIGH", 3: "HIGH"}
        result.append({
            "event_id": e.event_id if hasattr(e, "event_id") else e.id,
            "currency": e.currency if hasattr(e, "currency") else "",
            "event_name": e.event_name if hasattr(e, "event_name") else str(e),
            "time": datetime.fromtimestamp(e.time, tz=timezone.utc).isoformat()
            if hasattr(e, "time")
            else "",
            "importance": importance_map.get(
                getattr(e, "importance", 0), "LOW"
            ),
            "actual": str(getattr(e, "actual_value", "")),
            "forecast": str(getattr(e, "forecast_value", "")),
            "previous": str(getattr(e, "previous_value", "")),
        })
    return result


def _pip_size(symbol):
    """Return pip size for a symbol."""
    if "JPY" in symbol:
        return 0.01
    return 0.0001
