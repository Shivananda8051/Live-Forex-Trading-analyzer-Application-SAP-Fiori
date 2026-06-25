"""
Risk calculator — computes position size, pip value, and R:R options.
"""


# Approximate pip values per standard lot (100,000 units) in USD
# These are approximate; exact values depend on account currency and live rates
PIP_VALUES = {
    "EURUSD": 10.0,
    "GBPUSD": 10.0,
    "AUDUSD": 10.0,
    "NZDUSD": 10.0,
    "USDCHF": 10.0,
    "USDCAD": 10.0,
    "USDJPY": 6.7,  # approximate
    "GBPJPY": 6.7,
    "EURJPY": 6.7,
    "XAUUSD": 10.0,
}


def get_pip_size(pair):
    """Return pip size for a currency pair."""
    if "JPY" in pair:
        return 0.01
    if "XAU" in pair:
        return 0.1
    return 0.0001


def get_pip_value(pair):
    """Return approximate pip value per standard lot in USD."""
    return PIP_VALUES.get(pair, 10.0)


def calculate_position(balance, risk_pct, sl_pips, pair):
    """
    Calculate position size and risk metrics.

    Args:
        balance: Account balance
        risk_pct: Risk percentage (e.g., 1.0 for 1%)
        sl_pips: Stop loss distance in pips
        pair: Currency pair symbol

    Returns:
        Dict with risk_amount, lot_size, sl_pips, tp options at various R:R
    """
    if sl_pips <= 0 or risk_pct <= 0 or balance <= 0:
        return {"error": "Invalid inputs"}

    risk_amount = balance * (risk_pct / 100)
    pip_value = get_pip_value(pair)
    lot_size = risk_amount / (sl_pips * pip_value)

    return {
        "balance": balance,
        "risk_pct": risk_pct,
        "risk_amount": round(risk_amount, 2),
        "lot_size": round(lot_size, 2),
        "sl_pips": sl_pips,
        "pip_value_per_lot": pip_value,
        "pair": pair,
        "tp_options": {
            "1:1": round(sl_pips * 1, 1),
            "1:2": round(sl_pips * 2, 1),
            "1:3": round(sl_pips * 3, 1),
            "1:5": round(sl_pips * 5, 1),
        },
        "max_loss": round(risk_amount, 2),
        "potential_profit": {
            "1:1": round(risk_amount * 1, 2),
            "1:2": round(risk_amount * 2, 2),
            "1:3": round(risk_amount * 3, 2),
            "1:5": round(risk_amount * 5, 2),
        },
    }
