import pandas as pd
from bot.futures_data import normalize_funding_rates


def test_funding_rates_normalize_sort_and_deduplicate():
    rows = [
        {"timestamp": 1735718400000, "symbol": "BTC/USDT:USDT", "fundingRate": "0.0002"},
        {"timestamp": 1735689600000, "symbol": "BTC/USDT:USDT", "fundingRate": "-0.0001"},
        {"timestamp": 1735718400000, "symbol": "BTC/USDT:USDT", "fundingRate": "0.0003"},
    ]
    result = normalize_funding_rates(rows)
    assert len(result) == 2
    assert result.timestamp.is_monotonic_increasing
    assert result.iloc[-1].funding_rate == 0.0003
    assert str(result.timestamp.dt.tz) == "UTC"


def test_empty_funding_response_is_explicit_empty_frame():
    result = normalize_funding_rates([])
    assert list(result.columns) == ["timestamp", "symbol", "funding_rate"]
    assert result.empty
