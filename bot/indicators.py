import pandas as pd

REQUIRED = {"timestamp", "open", "high", "low", "close", "volume"}

def validate_ohlcv(df):
    missing = REQUIRED - set(df.columns)
    if missing: raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")
    if df.empty: raise ValueError("OHLCV data is empty")
    numeric = ["open", "high", "low", "close", "volume"]
    if df[numeric].isna().any().any(): raise ValueError("OHLCV contains null numeric values")
    if (df[["open", "high", "low", "close"]] <= 0).any().any(): raise ValueError("Prices must be positive")
    if (df["high"] < df[["open", "close", "low"]].max(axis=1)).any(): raise ValueError("Invalid candle high")
    if (df["low"] > df[["open", "close", "high"]].min(axis=1)).any(): raise ValueError("Invalid candle low")
    ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    if ts.isna().any() or not ts.is_monotonic_increasing or ts.duplicated().any(): raise ValueError("Timestamps must be valid, unique and chronological")

def add_indicators(df, fast=20, slow=50, rsi_period=14, atr_period=14):
    validate_ohlcv(df)
    out = df.copy()
    out["ema_fast"] = out["close"].ewm(span=fast, adjust=False).mean()
    out["ema_slow"] = out["close"].ewm(span=slow, adjust=False).mean()
    delta = out["close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/rsi_period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/rsi_period, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    out["rsi"] = 100 - (100 / (1 + rs))
    prev = out["close"].shift(1)
    tr = pd.concat([out["high"]-out["low"], (out["high"]-prev).abs(), (out["low"]-prev).abs()], axis=1).max(axis=1)
    out["atr"] = tr.ewm(alpha=1/atr_period, adjust=False).mean()
    return out
