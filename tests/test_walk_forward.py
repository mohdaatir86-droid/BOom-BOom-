import pytest
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


def test_evaluate_walk_forward_equity_reset_and_held_out_only(monkeypatch):
    """Each fold resets equity; only trades with entry inside the test window are scored."""
    candles = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=20, freq="h", tz="UTC"),
        "open": [100.0] * 20, "high": [101.0] * 20, "low": [99.0] * 20,
        "close": [100.0] * 20, "volume": [1.0] * 20,
    })

    def fake_run(segment, config=None, funding_df=None, funding_mark_price_column=None, trade_start_time=None):
        start = pd.to_datetime(trade_start_time, utc=True)
        trades = [{
            "entry_time": start.isoformat(),
            "exit_time": (start + pd.Timedelta(hours=1)).isoformat(),
            "entry": 100.0, "exit": 101.0, "qty": 1.0,
            "initial_risk": 2.0, "pnl_net": 10.0,
            "pnl_net_before_funding": 10.0, "funding_pnl_estimate": 0.0,
            "pnl_net_after_funding_estimate": 10.0, "reason": "target",
        }]
        return {
            "trades": 1, "final_equity": 10010.0, "net_pnl": 10.0,
            "return_pct": 0.1, "max_drawdown_pct": 0.0, "profit_factor": None,
            "funding_warning": None, "trades_detail": trades,
        }

    monkeypatch.setattr(wf, "run_backtest", fake_run)
    result = wf.evaluate_walk_forward(
        candles, BotConfig(initial_equity=10_000),
        train_size=5, test_size=3, step_size=3,
    )
    assert result["fold_count"] >= 1
    assert result["out_of_sample_trade_count"] == result["fold_count"]
    assert result["out_of_sample_net_pnl"] == pytest.approx(10.0 * result["fold_count"])
    for fold in result["folds"]:
        assert fold["trade_count"] == 1
        assert fold["net_pnl"] == pytest.approx(10.0)
