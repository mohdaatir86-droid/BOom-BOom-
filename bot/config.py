from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class BotConfig:
    initial_equity: float = 10_000.0
    risk_per_trade: float = 0.0025
    daily_loss_limit: float = 0.015
    fee_rate: float = 0.0006
    slippage_rate: float = 0.0005
    fast_ema: int = 20
    slow_ema: int = 50
    rsi_period: int = 14
    rsi_long_min: float = 50.0
    rsi_long_max: float = 70.0
    atr_period: int = 14
    stop_atr_multiple: float = 2.0

    def __post_init__(self):
        for name in ("initial_equity", "risk_per_trade", "daily_loss_limit",
                     "fast_ema", "slow_ema", "rsi_period", "atr_period", "stop_atr_multiple"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isfinite(float(value)) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if self.fast_ema >= self.slow_ema:
            raise ValueError("fast_ema must be less than slow_ema")
        for name in ("fee_rate", "slippage_rate"):
            value = getattr(self, name)
            if not isfinite(value) or not 0 <= value < 1:
                raise ValueError(f"{name} must be finite and in [0, 1)")
        if not 0 < self.risk_per_trade <= 1:
            raise ValueError("risk_per_trade must be in (0, 1]")
        if not 0 < self.daily_loss_limit <= 1:
            raise ValueError("daily_loss_limit must be in (0, 1]")
        if not 0 <= self.rsi_long_min <= self.rsi_long_max <= 100:
            raise ValueError("RSI bounds must satisfy 0 <= min <= max <= 100")
