import pytest
from bot.metrics import summarize_trades, equity_curve


def test_expectancy_and_loss_streak_metrics():
    result = summarize_trades([
        {"pnl_net": 20.0, "initial_risk": 10.0},
        {"pnl_net": -10.0, "initial_risk": 10.0},
        {"pnl_net": -5.0, "initial_risk": 10.0},
        {"pnl_net": 30.0, "initial_risk": 10.0},
    ], 1000)
    assert result["trade_count"] == 4
    assert result["net_pnl"] == 35.0
    assert result["expectancy_per_trade"] == 8.75
    assert result["expectancy_r"] == 0.875
    assert result["max_consecutive_losses"] == 2
    assert result["profit_factor"] == pytest.approx(50 / 15, rel=1e-3)


def test_empty_trades_are_safe():
    result = summarize_trades([], 1000)
    assert result["trade_count"] == 0
    assert result["expectancy_r"] is None


def test_equity_curve_drawdown():
    curve = equity_curve([{"pnl_net": 10}, {"pnl_net": -20}], 100)
    assert curve.iloc[-1].equity == 90
    assert curve.iloc[-1].drawdown_pct == pytest.approx(20 / 110 * 100)
