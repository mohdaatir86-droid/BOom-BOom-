"""Performance metrics for research results; metrics do not imply future profitability."""
from __future__ import annotations
from math import sqrt
import pandas as pd


def summarize_trades(trades, initial_equity: float) -> dict:
    if initial_equity <= 0:
        raise ValueError("initial_equity must be positive")
    if not trades:
        return {
            "trade_count": 0, "net_pnl": 0.0, "return_pct": 0.0,
            "win_rate_pct": 0.0, "profit_factor": None,
            "expectancy_per_trade": 0.0, "expectancy_r": None,
            "avg_win": None, "avg_loss": None, "max_consecutive_losses": 0,
        }
    df = pd.DataFrame(trades)
    if "pnl_net" not in df:
        raise ValueError("trades must include pnl_net")
    pnl = pd.to_numeric(df["pnl_net"], errors="coerce")
    if pnl.isna().any():
        raise ValueError("pnl_net must be numeric and finite")
    pnl = pnl.astype(float)
    if not all(map(lambda x: abs(x) != float("inf"), pnl)):
        raise ValueError("pnl_net must be finite")
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    gross_profit, gross_loss = float(wins.sum()), abs(float(losses.sum()))
    loss_streak = max_streak = 0
    for value in pnl:
        if value <= 0:
            loss_streak += 1
            max_streak = max(max_streak, loss_streak)
        else:
            loss_streak = 0
    initial_risk = None
    if "initial_risk" in df:
        risk = pd.to_numeric(df["initial_risk"], errors="coerce")
        valid = risk > 0
        if valid.all():
            initial_risk = risk.astype(float)
    expectancy_r = float((pnl / initial_risk).mean()) if initial_risk is not None else None
    return {
        "trade_count": int(len(pnl)),
        "net_pnl": round(float(pnl.sum()), 4),
        "return_pct": round(float(pnl.sum() / initial_equity * 100), 4),
        "win_rate_pct": round(float((pnl > 0).mean() * 100), 3),
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else (None if gross_profit == 0 else "infinite"),
        "expectancy_per_trade": round(float(pnl.mean()), 4),
        "expectancy_r": round(expectancy_r, 4) if expectancy_r is not None else None,
        "avg_win": round(float(wins.mean()), 4) if len(wins) else None,
        "avg_loss": round(float(losses.mean()), 4) if len(losses) else None,
        "max_consecutive_losses": max_streak,
    }


def equity_curve(trades, initial_equity: float) -> pd.DataFrame:
    """Create realized-equity curve from chronologically ordered trades."""
    equity = float(initial_equity)
    rows = [{"trade_index": 0, "equity": equity, "drawdown_pct": 0.0}]
    peak = equity
    for i, trade in enumerate(trades, start=1):
        equity += float(trade["pnl_net"])
        peak = max(peak, equity)
        dd = (peak - equity) / peak * 100 if peak > 0 else 0.0
        rows.append({"trade_index": i, "equity": equity, "drawdown_pct": dd})
    return pd.DataFrame(rows)
