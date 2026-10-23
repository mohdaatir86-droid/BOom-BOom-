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



def test_price_filter_min_max_and_percent_price_band():
    rules = BinanceMarketRules.from_exchange_info({
        "symbol": "TESTUSDT", "status": "TRADING",
        "filters": [
            {"filterType": "PRICE_FILTER", "minPrice": "1", "maxPrice": "1000", "tickSize": "0.1"},
            {"filterType": "LOT_SIZE", "minQty": "0.1", "maxQty": "100", "stepSize": "0.1"},
            {"filterType": "MARKET_LOT_SIZE", "minQty": "0.1", "maxQty": "100", "stepSize": "0.1"},
            {"filterType": "PERCENT_PRICE", "multiplierUp": "1.1", "multiplierDown": "0.9"},
            {"filterType": "MIN_NOTIONAL", "minNotional": "5"},
        ],
    })
    assert rules.validate_order(1, 105, reference_price=100) == pytest.approx((1, 105))
    with pytest.raises(ValueError, match="upper band"):
        rules.validate_order(1, 111, reference_price=100)
    with pytest.raises(ValueError, match="reference_price"):
        rules.validate_order(1, 100)
    with pytest.raises(ValueError, match="minimum"):
        rules.validate_order(1, 0.5, reference_price=1)



def test_order_count_filters_are_parsed_and_enforced():
    rules = BinanceMarketRules.from_exchange_info({
        "symbol": "TESTUSDT", "status": "TRADING",
        "filters": [
            {"filterType": "PRICE_FILTER", "minPrice": "1", "maxPrice": "1000", "tickSize": "0.1"},
            {"filterType": "LOT_SIZE", "minQty": "0.1", "maxQty": "100", "stepSize": "0.1"},
            {"filterType": "MARKET_LOT_SIZE", "minQty": "0.1", "maxQty": "100", "stepSize": "0.1"},
            {"filterType": "MAX_NUM_ORDERS", "limit": 5},
            {"filterType": "MAX_NUM_ALGO_ORDERS", "limit": 2},
        ],
    })
    rules.validate_order_capacity(open_orders=5, open_algo_orders=2)
    with pytest.raises(ValueError, match="MAX_NUM_ORDERS"):
        rules.validate_order_capacity(open_orders=6)
    with pytest.raises(ValueError, match="MAX_NUM_ALGO_ORDERS"):
        rules.validate_order_capacity(open_orders=1, open_algo_orders=3)
    with pytest.raises(ValueError, match="non-negative"):
        rules.validate_order_capacity(open_orders=-1)



def test_cross_margin_missing_or_invalid_mark_fails_with_clear_error():
    p = CrossPosition("BTCUSDT", "LONG", 1, 100, sample_brackets(), liquidation_fee_rate=0.001)
    account = CrossMarginAccount(100, [p])
    with pytest.raises(ValueError, match="missing mark prices"):
        account.equity({})
    with pytest.raises(ValueError, match="mark price"):
        account.maintenance_margin({"BTCUSDT": 0})
