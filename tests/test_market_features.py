import pandas as pd
import pytest

from bot.market_features import align_open_interest


def test_alignment_never_uses_future_open_interest():
    candles = pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"]),
        "close": [100, 101],
    })
    oi = pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-01-01T00:30:00Z", "2026-01-01T01:00:00Z"]),
        "sum_open_interest": [12.0, 15.0],
        "sum_open_interest_value": [1200.0, 1515.0],
    })
    result = align_open_interest(candles, oi)
    assert pd.isna(result.loc[0, "open_interest"])
    assert result.loc[1, "open_interest"] == 15.0


def test_alignment_uses_latest_prior_snapshot_and_restores_order():
    candles = pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-01-01T02:00:00Z", "2026-01-01T01:00:00Z"]),
        "close": [102, 101],
    })
    oi = pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-01-01T00:00:00Z", "2026-01-01T01:30:00Z"]),
        "sum_open_interest": [10.0, 14.0],
        "sum_open_interest_value": [1000.0, 1400.0],
    })
    result = align_open_interest(candles, oi)
    assert result["close"].tolist() == [102, 101]
    assert result["open_interest"].tolist() == [14.0, 10.0]


def test_tolerance_prevents_stale_snapshot_match():
    candles = pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01T04:00:00Z"])})
    oi = pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-01-01T00:00:00Z"]),
        "sum_open_interest": [10.0],
        "sum_open_interest_value": [1000.0],
    })
    result = align_open_interest(candles, oi, tolerance="1h")
    assert pd.isna(result.loc[0, "open_interest"])


def test_invalid_timestamps_raise():
    candles = pd.DataFrame({"timestamp": ["not-a-date"]})
    oi = pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-01-01T00:00:00Z"]),
        "sum_open_interest": [10.0],
        "sum_open_interest_value": [1000.0],
    })
    with pytest.raises(ValueError, match="valid and non-null"):
        align_open_interest(candles, oi)
