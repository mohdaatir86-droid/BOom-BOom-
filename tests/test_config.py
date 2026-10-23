import pytest
from bot.config import BotConfig

@pytest.mark.parametrize("kwargs", [
    {"initial_equity": 0}, {"risk_per_trade": 0}, {"risk_per_trade": 1.1},
    {"daily_loss_limit": 0}, {"fee_rate": -0.1}, {"slippage_rate": 1.0},
    {"fast_ema": 50, "slow_ema": 20}, {"rsi_long_min": 80, "rsi_long_max": 70},
])
def test_invalid_config_rejected(kwargs):
    with pytest.raises(ValueError):
        BotConfig(**kwargs)

def test_default_config_is_valid():
    assert BotConfig().initial_equity > 0
