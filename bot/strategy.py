from .config import BotConfig
from .indicators import add_indicators

def generate_signals(df, config=None):
    # Research hypothesis only: long-only EMA trend + RSI filter.
    cfg = config or BotConfig()
    out = add_indicators(df, cfg.fast_ema, cfg.slow_ema, cfg.rsi_period, cfg.atr_period)
    out["long_signal"] = ((out["ema_fast"] > out["ema_slow"]) & (out["rsi"] >= cfg.rsi_long_min) & (out["rsi"] <= cfg.rsi_long_max))
    out.loc[out.index[:max(cfg.slow_ema, cfg.rsi_period, cfg.atr_period)+1], "long_signal"] = False
    return out
