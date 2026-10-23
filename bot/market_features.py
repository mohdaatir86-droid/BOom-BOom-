"""Leakage-safe alignment of public open-interest snapshots to candle data."""
from __future__ import annotations

import pandas as pd


def align_open_interest(
    candles: pd.DataFrame,
    open_interest: pd.DataFrame,
    *,
    timestamp_column: str = "timestamp",
    tolerance: str | pd.Timedelta | None = None,
) -> pd.DataFrame:
    """Attach the latest OI snapshot available at each candle timestamp.

    Uses backward as-of matching only: future OI observations are never attached.
    Inputs may use naive or timezone-aware timestamps; all are normalized to UTC.
    Original candle order is restored in the returned frame.
    """
    if timestamp_column not in candles or timestamp_column not in open_interest:
        raise ValueError(f"Both inputs must contain {timestamp_column!r}")
    required = {"sum_open_interest", "sum_open_interest_value"}
    if not required.issubset(open_interest.columns):
        raise ValueError(f"open_interest must contain {sorted(required)}")

    left = candles.copy()
    right = open_interest[[timestamp_column, *sorted(required)]].copy()
    left["_original_order"] = range(len(left))
    left[timestamp_column] = pd.to_datetime(left[timestamp_column], utc=True, errors="coerce")
    right[timestamp_column] = pd.to_datetime(right[timestamp_column], utc=True, errors="coerce")
    if left[timestamp_column].isna().any() or right[timestamp_column].isna().any():
        raise ValueError("Timestamps must be valid and non-null")
    if left.empty:
        return left.drop(columns=["_original_order"]).reset_index(drop=True)

    left = left.sort_values(timestamp_column)
    right = right.sort_values(timestamp_column).drop_duplicates(timestamp_column, keep="last")
    tol = pd.Timedelta(tolerance) if tolerance is not None else None
    merged = pd.merge_asof(
        left, right, on=timestamp_column, direction="backward",
        tolerance=tol, allow_exact_matches=True, suffixes=("", "_oi"),
    )
    merged = merged.sort_values("_original_order").drop(columns=["_original_order"])
    merged = merged.rename(columns={
        "sum_open_interest": "open_interest",
        "sum_open_interest_value": "open_interest_value",
    })
    merged["open_interest_change"] = merged["open_interest"].diff()
    merged["open_interest_pct_change"] = merged["open_interest"].pct_change().replace(
        [float("inf"), float("-inf")], float("nan")
    )
    return merged.reset_index(drop=True)
