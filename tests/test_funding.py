import pandas as pd
import pytest
from bot.funding import apply_funding_to_trades


def test_long_pays_positive_and_receives_negative_funding():
    trades = [{
        "entry_time": "2025-01-01T00:00:00Z",
        "exit_time": "2025-01-01T16:00:00Z",
        "entry": 100.0, "qty": 2.0, "pnl_net": 10.0,
    }]
    funding = pd.DataFrame({
        "timestamp": pd.to_datetime(["2025-01-01T08:00:00Z", "2025-01-01T16:00:00Z"]),
        "funding_rate": [0.001, -0.0005],
    })
    result = apply_funding_to_trades(trades, funding)[0]
    assert result["funding_events_counted"] == 2
    assert result["funding_pnl_estimate"] == pytest.approx(-0.1)
    assert result["pnl_net_after_funding_estimate"] == pytest.approx(9.9)
    assert result["funding_mark_price_method"] == "entry_price_proxy"


def test_funding_before_entry_is_not_counted():
    trades = [{
        "entry_time": "2025-01-01T09:00:00Z",
        "exit_time": "2025-01-01T17:00:00Z",
        "entry": 100.0, "qty": 1.0, "pnl_net": 2.0,
    }]
    funding = pd.DataFrame({
        "timestamp": pd.to_datetime(["2025-01-01T08:00:00Z"]),
        "funding_rate": [0.01],
    })
    result = apply_funding_to_trades(trades, funding)[0]
    assert result["funding_events_counted"] == 0
    assert result["pnl_net_after_funding_estimate"] == 2.0


def test_mark_price_column_is_used_for_funding_estimate():
    trades = [{
        "entry_time": "2025-01-01T00:00:00Z",
        "exit_time": "2025-01-01T08:00:00Z",
        "entry": 100.0, "qty": 2.0, "pnl_net": 0.0,
    }]
    funding = pd.DataFrame({
        "timestamp": pd.to_datetime(["2025-01-01T08:00:00Z"]),
        "funding_rate": [0.001],
        "mark_price": [120.0],
    })
    result = apply_funding_to_trades(trades, funding, mark_price_column="mark_price")[0]
    assert result["funding_pnl_estimate"] == pytest.approx(-0.24)
    assert result["funding_mark_price_method"] == "mark_price_column"
