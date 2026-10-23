"""Rule-based candlestick features for research; patterns are not standalone trade signals."""
from __future__ import annotations
import pandas as pd

def add_candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing candle columns: {sorted(missing)}")
    out = df.copy()
    o, h, l, c = (out[k].astype(float) for k in ("open", "high", "low", "close"))
    body = (c - o).abs()
    candle_range = (h - l).replace(0, float("nan"))
    upper = h - pd.concat([o, c], axis=1).max(axis=1)
    lower = pd.concat([o, c], axis=1).min(axis=1) - l
    bullish, bearish = c > o, c < o
    prev_o, prev_c = o.shift(1), c.shift(1)
    prev_body = (prev_c - prev_o).abs()
    out["candle_doji"] = (body / candle_range <= 0.10).fillna(False)
    out["candle_hammer"] = ((lower >= 2 * body) & (upper <= body) & (body / candle_range <= 0.40)).fillna(False)
    out["candle_shooting_star"] = ((upper >= 2 * body) & (lower <= body) & (body / candle_range <= 0.40)).fillna(False)
    out["candle_bullish_engulfing"] = (bearish.shift(1, fill_value=False) & bullish & (o <= prev_c) & (c >= prev_o) & (body > prev_body)).fillna(False)
    out["candle_bearish_engulfing"] = (bullish.shift(1, fill_value=False) & bearish & (o >= prev_c) & (c <= prev_o) & (body > prev_body)).fillna(False)
    first_mid_2 = (o.shift(2) + c.shift(2)) / 2
    first_bull, first_bear = c.shift(2) > o.shift(2), c.shift(2) < o.shift(2)
    middle_small = body.shift(1) <= (body.shift(2) * 0.5)
    out["candle_morning_star"] = (first_bear & middle_small & bullish & (c >= first_mid_2)).fillna(False)
    out["candle_evening_star"] = (first_bull & middle_small & bearish & (c <= first_mid_2)).fillna(False)
    return out
