from collections import Counter

from django.db.models import Avg, Sum
from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import Trade
from .serializers import TradeSerializer


class TradeViewSet(viewsets.ModelViewSet):
    """CRUD for trade journal entries."""

    serializer_class = TradeSerializer
    queryset = Trade.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        pair = self.request.query_params.get("pair")
        result = self.request.query_params.get("result")
        if pair:
            qs = qs.filter(pair=pair)
        if result:
            qs = qs.filter(result=result)
        return qs


@api_view(["GET"])
def analytics(request):
    """
    GET /api/journal/analytics/
    Compute trading statistics from journal entries.
    """
    trades = Trade.objects.exclude(result="OPEN")

    if not trades.exists():
        return Response({"message": "No closed trades yet"})

    wins = trades.filter(result="WIN")
    losses = trades.filter(result="LOSS")
    breakeven = trades.filter(result="BE")

    total = trades.count()
    win_count = wins.count()
    loss_count = losses.count()

    # Win rate
    win_rate = round(win_count / total * 100, 1) if total > 0 else 0

    # Profit factor
    gross_profit = wins.aggregate(s=Sum("pnl"))["s"] or 0
    gross_loss = abs(losses.aggregate(s=Sum("pnl"))["s"] or 0)
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0

    # Average RR
    rr_values = [t.risk_reward for t in trades if t.risk_reward is not None]
    avg_rr = round(sum(rr_values) / len(rr_values), 2) if rr_values else 0

    # Best/worst pair
    pair_stats = {}
    for t in trades:
        if t.pair not in pair_stats:
            pair_stats[t.pair] = {"wins": 0, "total": 0}
        pair_stats[t.pair]["total"] += 1
        if t.result == "WIN":
            pair_stats[t.pair]["wins"] += 1

    pair_wr = {p: s["wins"] / s["total"] * 100 for p, s in pair_stats.items() if s["total"] >= 3}
    best_pair = max(pair_wr, key=pair_wr.get) if pair_wr else "N/A"
    worst_pair = min(pair_wr, key=pair_wr.get) if pair_wr else "N/A"

    # Best session
    session_stats = {}
    for t in trades:
        sess = t.session or "Unknown"
        if sess not in session_stats:
            session_stats[sess] = {"wins": 0, "total": 0}
        session_stats[sess]["total"] += 1
        if t.result == "WIN":
            session_stats[sess]["wins"] += 1

    session_wr = {s: d["wins"] / d["total"] * 100 for s, d in session_stats.items() if d["total"] >= 3}
    best_session = max(session_wr, key=session_wr.get) if session_wr else "N/A"

    # Avg trade score
    avg_score = trades.filter(trade_score__isnull=False).aggregate(a=Avg("trade_score"))["a"] or 0

    # Consecutive wins/losses
    results_list = list(trades.order_by("created_at").values_list("result", flat=True))
    max_consec_wins = _max_consecutive(results_list, "WIN")
    max_consec_losses = _max_consecutive(results_list, "LOSS")

    # Monthly PnL
    monthly_pnl = {}
    for t in trades:
        month_key = t.created_at.strftime("%Y-%m")
        monthly_pnl[month_key] = monthly_pnl.get(month_key, 0) + (t.pnl or 0)

    return Response({
        "total_trades": total,
        "wins": win_count,
        "losses": loss_count,
        "breakeven": breakeven.count(),
        "win_rate": win_rate,
        "avg_rr": avg_rr,
        "profit_factor": profit_factor,
        "total_pnl": round(trades.aggregate(s=Sum("pnl"))["s"] or 0, 2),
        "best_pair": best_pair,
        "worst_pair": worst_pair,
        "best_session": best_session,
        "avg_trade_score": round(avg_score, 1),
        "max_consecutive_wins": max_consec_wins,
        "max_consecutive_losses": max_consec_losses,
        "monthly_pnl": monthly_pnl,
        "pair_win_rates": pair_wr,
    })


@api_view(["GET"])
def score_validation(request):
    """
    GET /api/journal/score-validation/
    Validate if the trade quality score correlates with wins.
    """
    trades = Trade.objects.exclude(result="OPEN").filter(trade_score__isnull=False)

    if trades.count() < 30:
        return Response({"message": f"Need at least 30 scored trades ({trades.count()} so far)"})

    high_score = trades.filter(trade_score__gte=70)
    low_score = trades.filter(trade_score__lt=70)

    high_wr = high_score.filter(result="WIN").count() / max(high_score.count(), 1) * 100
    low_wr = low_score.filter(result="WIN").count() / max(low_score.count(), 1) * 100

    return Response({
        "total_scored_trades": trades.count(),
        "high_score_trades": high_score.count(),
        "high_score_win_rate": round(high_wr, 1),
        "low_score_trades": low_score.count(),
        "low_score_win_rate": round(low_wr, 1),
        "score_adds_value": high_wr > low_wr,
    })


def _max_consecutive(results, target):
    """Calculate max consecutive occurrences of target in results list."""
    max_count = 0
    current = 0
    for r in results:
        if r == target:
            current += 1
            max_count = max(max_count, current)
        else:
            current = 0
    return max_count
