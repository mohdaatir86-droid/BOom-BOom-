from dataclasses import dataclass

@dataclass(frozen=True)
class BotConfig:
    initial_equity: float = 10_000.0
    risk_per_trade: float = 0.0025  # candidate 0.25%; validate before use
    daily_loss_limit: float = 0.015 # candidate 1.5%; realized-PnL guard
    fee_rate: float = 0.0006       # illustrative per-side fee; set to venue
    slippage_rate: float = 0.0005   # illustrative assumption
    fast_ema: int = 20
    slow_ema: int = 50
    rsi_period: int = 14
    rsi_long_min: float = 50.0
    rsi_long_max: float = 70.0
    atr_period: int = 14
    stop_atr_multiple: float = 2.0
