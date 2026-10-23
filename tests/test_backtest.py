import pandas as pd
import pytest

import bot.backtest as backtest
from bot.config import BotConfig


def test_backtest_does_not_reenter_on_same_bar_as_exit(monkeypatch):
    candles = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=4, freq="h", tz="UTC"),
        "open": [100.0, 100.0, 100.0, 100.0],
        "high": [101.0, 101.0, 101.0, 101.0],
        "low": [99.0, 99.0, 97.0, 99.0],
        "close": [100.0, 100.0, 99.0, 100.0],
        "volume": [1.0, 1.0, 1.0, 1.0],
    })
    signalled = candles.copy()
    signalled["atr"] = [1.0, 1.0, 1.0, 1.0]
    signalled["long_signal"] = [True, True, False, False]
    monkeypatch.setattr(backtest, "generate_signals", lambda df, cfg: signalled.copy())

    result = backtest.run_backtest(
        candles,
        BotConfig(initial_equity=10_000, risk_per_trade=0.01, fee_rate=0.0, slippage_rate=0.0),
    )

    # First trade exits on candle 2; a second entry cannot be filled at that
    # candle's open after using its later low to decide the prior trade exited.
    assert result["trades"] == 1
    assert result["trades_detail"][0]["reason"] == "stop"



def test_funding_adjustment_is_reflected_in_final_equity(monkeypatch):
    candles = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=4, freq="h", tz="UTC"),
        "open": [100.0] * 4, "high": [101.0] * 4, "low": [99.0] * 4,
        "close": [100.0] * 4, "volume": [1.0] * 4,
    })
    signalled = candles.copy()
    signalled["atr"] = [1.0] * 4
    signalled["long_signal"] = [True, False, False, False]
    monkeypatch.setattr(backtest, "generate_signals", lambda df, cfg: signalled.copy())
    funding = pd.DataFrame({
        "timestamp": pd.to_datetime(["2025-01-01T02:00:00Z"]),
        "funding_rate": [0.01],
    })
    result = backtest.run_backtest(
        candles,
        BotConfig(initial_equity=10_000, risk_per_trade=0.01, fee_rate=0.0, slippage_rate=0.0),
        funding_df=funding,
    )
    trade = result["trades_detail"][0]
    assert trade["pnl_net"] == pytest.approx(trade["pnl_net_after_funding_estimate"])
    assert trade["pnl_net"] < trade["pnl_net_before_funding"]
    assert result["final_equity"] == pytest.approx(10_000 + trade["pnl_net"])


def test_stop_gap_fills_at_open_not_stop(monkeypatch):
    candles = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=4, freq="h", tz="UTC"),
        "open": [100.0, 100.0, 95.0, 100.0],
        "high": [101.0, 101.0, 97.0, 101.0],
        "low": [99.0, 99.0, 94.0, 99.0],
        "close": [100.0, 100.0, 96.0, 100.0],
        "volume": [1.0, 1.0, 1.0, 1.0],
    })
    signalled = candles.copy()
    signalled["atr"] = [1.0] * 4
    signalled["long_signal"] = [True, False, False, False]
    monkeypatch.setattr(backtest, "generate_signals", lambda df, cfg: signalled.copy())
    result = backtest.run_backtest(
        candles,
        BotConfig(initial_equity=10_000, risk_per_trade=0.01, fee_rate=0.0, slippage_rate=0.0),
    )
    trade = result["trades_detail"][0]
    assert trade["reason"] == "stop_gap"
    assert trade["exit"] == 95.0
