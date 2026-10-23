import pandas as pd
from bot.config import BotConfig
import bot.walk_forward as wf


def test_walk_forward_scores_only_test_period_and_retains_warmup(monkeypatch):
    candles = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=10, freq="h", tz="UTC"),
        "open": [100.0] * 10, "high": [101.0] * 10, "low": [99.0] * 10,
        "close": [100.0] * 10, "volume": [1.0] * 10,
    })
    calls = []

    def fake_backtest(segment, config, **kwargs):
        calls.append((segment.copy(), kwargs["trade_start_time"]))
        start = pd.to_datetime(kwargs["trade_start_time"], utc=True)
        return {
            "trades_detail": [{
                "entry_time": start.isoformat(), "exit_time": start.isoformat(),
                "entry": 100.0, "exit": 101.0, "qty": 1.0,
                "initial_risk": 1.0, "pnl_net": 1.0, "reason": "target",
            }]
        }

    monkeypatch.setattr(wf, "run_backtest", fake_backtest)
    result = wf.evaluate_walk_forward(candles, BotConfig(), train_size=4, test_size=2)
    assert result["fold_count"] == 3
    assert result["out_of_sample_trade_count"] == 3
    assert len(calls[0][0]) == 6
    assert calls[0][1] == pd.Timestamp("2026-01-01T04:00:00Z")
