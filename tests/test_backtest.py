import pandas as pd

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
