from bot.risk import position_size, RiskState, validate_long_trade

def test_position_size_respects_budget():
    qty = position_size(10000, 100, 95, 0.01, quantity_step=0.001)
    assert qty > 0 and qty*(100-95) <= 100

def test_invalid_prices_return_zero():
    assert position_size(1000, 0, 5, 0.01) == 0
    assert position_size(1000, 100, 100, 0.01) == 0

def test_trade_geometry():
    assert validate_long_trade(100, 95, 110)
    assert not validate_long_trade(100, 105, 110)

def test_daily_loss_halts_entries():
    state = RiskState(10000)
    state.record_realized_pnl(-151, 0.015)
    assert state.halted and not state.can_open_new_position()


def test_unrealized_daily_loss_halts_new_entries():
    state = RiskState(10000)
    state.check_daily_loss(-151, 0.015)
    assert state.halted
    assert state.halt_reason == "daily_loss_limit"
    assert not state.can_open_new_position()


def test_realized_and_unrealized_loss_are_combined():
    state = RiskState(10000)
    state.record_realized_pnl(-80, 0.015)
    state.check_daily_loss(-71, 0.015)
    assert state.halted
