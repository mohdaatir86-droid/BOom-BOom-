import pytest

from bot.binance_futures_simulator import (
    BinanceMarketRules, CrossMarginAccount, CrossPosition, MaintenanceBracket,
    bracket_for_notional, brackets_from_leverage_response,
)


def sample_brackets():
    return (
        MaintenanceBracket(0, 50_000, 0.004, 0),
        MaintenanceBracket(50_000, 250_000, 0.005, 50),
    )


def test_maintenance_bracket_uses_cumulative_amount():
    brackets = sample_brackets()
    assert bracket_for_notional(brackets, 10_000).maintenance_margin(10_000) == pytest.approx(40)
    assert bracket_for_notional(brackets, 60_000).maintenance_margin(60_000) == pytest.approx(250)


def test_parse_binance_leverage_bracket_payload():
    parsed = brackets_from_leverage_response([{
        "symbol": "BTCUSDT",
        "brackets": [
            {"bracket": 1, "initialLeverage": 125, "notionalFloor": "0",
             "notionalCap": "50000", "maintMarginRatio": "0.004", "cum": "0"},
            {"bracket": 2, "initialLeverage": 100, "notionalFloor": "50000",
             "notionalCap": "250000", "maintMarginRatio": "0.005", "cum": "50"},
        ],
    }])
    assert parsed["BTCUSDT"][1].maintenance_margin(60_000) == pytest.approx(250)


def test_market_rules_parse_and_round_market_quantity_separately():
    rules = BinanceMarketRules.from_exchange_info({
        "symbol": "BTCUSDT", "status": "TRADING",
        "filters": [
            {"filterType": "PRICE_FILTER", "tickSize": "0.10"},
            {"filterType": "LOT_SIZE", "minQty": "0.001", "maxQty": "100", "stepSize": "0.001"},
            {"filterType": "MARKET_LOT_SIZE", "minQty": "0.01", "maxQty": "50", "stepSize": "0.01"},
            {"filterType": "MIN_NOTIONAL", "notional": "5", "minNotional": "5"},
        ],
    })
    assert rules.validate_order(0.059, 100, market=True) == pytest.approx((0.05, 100))
    with pytest.raises(ValueError, match="minimum"):
        rules.validate_order(0.009, 100, market=True)
    with pytest.raises(ValueError, match="TRADING"):
        BinanceMarketRules(**{**rules.__dict__, "status": "BREAK"}).validate_order(1, 100)


def test_cross_margin_equity_and_portfolio_maintenance():
    p1 = CrossPosition("BTCUSDT", "LONG", 1, 100, (
        MaintenanceBracket(0, 1_000, 0.01, 0),
    ), liquidation_fee_rate=0.001)
    p2 = CrossPosition("ETHUSDT", "SHORT", 2, 50, (
        MaintenanceBracket(0, 1_000, 0.01, 0),
    ), liquidation_fee_rate=0.001)
    account = CrossMarginAccount(100, [p1, p2])
    marks = {"BTCUSDT": 90, "ETHUSDT": 55}
    assert account.equity(marks) == pytest.approx(80)
    assert account.maintenance_margin(marks) == pytest.approx(2)
    assert account.liquidation_fee_reserve(marks) == pytest.approx(0.2)
    assert not account.is_liquidation_triggered(marks)


def test_cross_margin_liquidation_price_moves_against_position():
    p = CrossPosition("BTCUSDT", "LONG", 1, 100, sample_brackets(), liquidation_fee_rate=0.001)
    account = CrossMarginAccount(20, [p])
    price = account.estimated_liquidation_price("BTCUSDT", {"BTCUSDT": 100})
    assert 70 < price < 100
    assert account.is_liquidation_triggered({"BTCUSDT": price - 0.01})


def test_invalid_brackets_and_missing_symbols_fail_closed():
    with pytest.raises(ValueError):
        brackets_from_leverage_response([{"symbol": "BTCUSDT", "brackets": []}])
    with pytest.raises(ValueError, match="outside"):
        bracket_for_notional(sample_brackets(), 300_000)
