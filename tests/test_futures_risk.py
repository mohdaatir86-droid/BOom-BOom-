import pytest

from bot.futures_risk import LinearFuturesPosition, LinearMarketRules


def test_long_and_short_liquidation_estimates_are_directional():
    long = LinearFuturesPosition(entry_price=100, quantity=2, leverage=10, maintenance_margin_rate=0.005)
    short = LinearFuturesPosition(entry_price=100, quantity=2, leverage=10, maintenance_margin_rate=0.005)
    assert long.estimated_liquidation_price("long") == pytest.approx(90.5)
    assert short.estimated_liquidation_price("short") == pytest.approx(109.5)


def test_pnl_and_margin_remaining():
    position = LinearFuturesPosition(entry_price=100, quantity=2, leverage=5, entry_fee_rate=0.001)
    assert position.notional == pytest.approx(200)
    assert position.estimated_initial_margin == pytest.approx(40)
    assert position.unrealized_pnl(110, "long") == pytest.approx(20)
    assert position.unrealized_pnl(90, "short") == pytest.approx(20)
    assert position.margin_remaining(110, "long") == pytest.approx(59.8)


@pytest.mark.parametrize("kwargs", [
    {"entry_price": 0, "quantity": 1, "leverage": 2},
    {"entry_price": 100, "quantity": -1, "leverage": 2},
    {"entry_price": 100, "quantity": 1, "leverage": 0.5},
    {"entry_price": 100, "quantity": 1, "leverage": 10, "maintenance_margin_rate": 0.1},
])
def test_invalid_positions_rejected(kwargs):
    with pytest.raises(ValueError):
        LinearFuturesPosition(**kwargs)


def test_invalid_side_rejected():
    position = LinearFuturesPosition(100, 1, 5)
    with pytest.raises(ValueError, match="side"):
        position.unrealized_pnl(101, "buy")


def test_market_rules_round_down_and_enforce_minimums():
    rules = LinearMarketRules(quantity_step=0.01, min_quantity=0.05, tick_size=0.1, min_notional=5)
    assert rules.round_quantity_down(1.239, 10) == pytest.approx(1.23)
    assert rules.round_price(10.19) == pytest.approx(10.1)
    assert rules.round_price(10.11, upward=True) == pytest.approx(10.2)
    with pytest.raises(ValueError, match="minimum"):
        rules.round_quantity_down(0.049, 100)
    with pytest.raises(ValueError, match="notional"):
        rules.round_quantity_down(0.1, 10)


def test_invalid_market_rules_rejected():
    with pytest.raises(ValueError):
        LinearMarketRules(quantity_step=0, min_quantity=1, tick_size=0.1)
