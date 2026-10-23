import pandas as pd
import pytest
import bot.backtest as backtest
from bot.config import BotConfig

def test_funding_event_is_applied_at_event_time_and_once(monkeypatch):
    candles = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=5, freq="8h", tz="UTC"),
        "open": [100.] * 5, "high": [101.] * 5, "low": [99.] * 5,
        "close": [100.] * 5, "volume": [1.] * 5,
    })
    signals = candles.copy()
    signals["atr"] = [1.] * len(candles)
    signals["long_signal"] = [True, False, False, False, False]
    monkeypatch.setattr(backtest, "generate_signals", lambda df, cfg: signals.copy())
    funding = pd.DataFrame({"timestamp": [candles.timestamp.iloc[2]], "funding_rate": [0.001], "mark": [120.]})
    result = backtest.run_backtest(candles, BotConfig(initial_equity=10000, fee_rate=0, slippage_rate=0), funding, "mark")
    trade = result["trades_detail"][0]
    assert trade["funding_pnl_estimate"] == pytest.approx(-trade["qty"] * 120 * 0.001)
    assert trade["pnl_net"] == pytest.approx(trade["pnl_net_before_funding"] + trade["funding_pnl_estimate"])
    assert result["final_equity"] == pytest.approx(10000 + trade["pnl_net"])
