import pandas as pd
import pytest

from bot.data import normalize_ohlcv


def test_normalize_sorts_deduplicates_and_uses_utc():
    rows = [
        [1735689600000, 100, 105, 99, 103, 10],
        [1735686000000, 98, 102, 97, 100, 12],
        [1735689600000, 100, 106, 99, 104, 11],
    ]
    result = normalize_ohlcv(rows)
    assert len(result) == 2
    assert result.timestamp.is_monotonic_increasing
    assert str(result.timestamp.dt.tz) == "UTC"
    assert result.iloc[-1].close == 104


def test_rejects_invalid_candle_geometry():
    rows = [
        [1735686000000, 100, 99, 95, 98, 1],
        [1735689600000, 98, 102, 97, 100, 1],
    ]
    with pytest.raises(ValueError, match="high"):
        normalize_ohlcv(rows)


def test_rejects_empty_exchange_response():
    with pytest.raises(ValueError, match="no OHLCV"):
        normalize_ohlcv([])
