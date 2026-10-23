"""Funding cost helpers for research. Mark-price use is approximate unless supplied."""
from __future__ import annotations
import pandas as pd


def apply_funding_to_trades(trades, funding, mark_price_column: str | None = None):
    """Return copied trade records with estimated funding PnL/cost applied.

    Funding timestamps are charged only when entry_time < timestamp <= exit_time.
    Positive funding means a long pays; negative funding means a long receives.
    If no mark price is supplied, entry price is used as a disclosed notional proxy.
    """
    required = {"timestamp", "funding_rate"}
    if not required.issubset(set(funding.columns)):
        raise ValueError(f"funding must contain columns: {sorted(required)}")
    rates = funding.copy()
    rates["timestamp"] = pd.to_datetime(rates["timestamp"], utc=True, errors="coerce")
    rates["funding_rate"] = pd.to_numeric(rates["funding_rate"], errors="coerce")
    if rates[["timestamp", "funding_rate"]].isna().any().any():
        raise ValueError("Funding timestamps/rates contain invalid values")
    if mark_price_column and mark_price_column not in rates:
        raise ValueError(f"Missing mark-price column: {mark_price_column}")
    results = []
    for trade in trades:
        item = dict(trade)
        entry_time = pd.to_datetime(item["entry_time"], utc=True, errors="coerce")
        exit_time = pd.to_datetime(item["exit_time"], utc=True, errors="coerce")
        if pd.isna(entry_time) or pd.isna(exit_time) or exit_time < entry_time:
            raise ValueError("Trade timestamps must be valid and exit cannot precede entry")
        entry = float(item["entry"])
        qty = float(item["qty"])
        active = rates[(rates["timestamp"] > entry_time) & (rates["timestamp"] <= exit_time)]
        total = 0.0
        for _, rate_row in active.iterrows():
            mark = float(rate_row[mark_price_column]) if mark_price_column else entry
            if mark <= 0:
                raise ValueError("Funding mark price must be positive")
            total += -qty * mark * float(rate_row["funding_rate"])
        item["funding_pnl_estimate"] = total
        item["pnl_net_after_funding_estimate"] = float(item["pnl_net"]) + total
        item["funding_events_counted"] = int(len(active))
        item["funding_mark_price_method"] = "provided_mark_price" if mark_price_column else "entry_price_proxy"
        results.append(item)
    return results
