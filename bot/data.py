"""Read-only public market-data downloader. No credentials or order endpoints are used."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def normalize_ohlcv(rows) -> pd.DataFrame:
    """Convert CCXT [ms, open, high, low, close, volume] rows into validated UTC candles."""
    if not rows:
        raise ValueError("Exchange returned no OHLCV candles.")
    df = pd.DataFrame(rows, columns=OHLCV_COLUMNS)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    for column in OHLCV_COLUMNS[1:]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    if df[OHLCV_COLUMNS].isna().any().any():
        raise ValueError("OHLCV response contains missing or non-numeric values.")
    df = df.drop_duplicates(subset=["timestamp"], keep="last")
    df = df.sort_values("timestamp").reset_index(drop=True)
    if len(df) < 2:
        raise ValueError("At least two distinct candles are required.")
    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("OHLC prices must be positive.")
    if (df["volume"] < 0).any():
        raise ValueError("Volume cannot be negative.")
    if (df["high"] < df[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("Invalid candle: high is below another OHLC value.")
    if (df["low"] > df[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("Invalid candle: low is above another OHLC value.")
    return df


def download_ohlcv(exchange_id="binance", symbol="BTC/USDT", timeframe="1h", limit=500):
    """Fetch recent public candles via CCXT. This function never submits orders."""
    if not isinstance(limit, int) or not 2 <= limit <= 1000:
        raise ValueError("limit must be an integer between 2 and 1000")
    import ccxt

    exchange_class = getattr(ccxt, exchange_id, None)
    if exchange_class is None or not callable(exchange_class):
        raise ValueError(f"Unsupported CCXT exchange: {exchange_id}")
    exchange = exchange_class({"enableRateLimit": True})
    if not exchange.has.get("fetchOHLCV"):
        raise ValueError(f"{exchange_id} does not support OHLCV fetching through CCXT")

    if exchange_id == "binance":
        # Only load spot markets: otherwise CCXT may call futures market metadata
        # (fapi.binance.com), which is unrelated to this spot OHLCV research flow.
        exchange.options["defaultType"] = "spot"
        exchange.options["fetchMarkets"] = ["spot"]
        # Official public market-data-only REST base; no authentication or orders.
        exchange.urls["api"]["public"] = "https://data-api.binance.vision/api/v3"

    exchange.load_markets()
    if symbol not in exchange.markets:
        raise ValueError(f"Symbol {symbol!r} is not listed on {exchange_id}")
    rows = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    return normalize_ohlcv(rows)


def main():
    parser = argparse.ArgumentParser(description="Download public crypto candles (read-only).")
    parser.add_argument("--exchange", default="binance", help="CCXT exchange id, e.g. binance")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--out", default="data/BTC_USDT_1h.csv")
    args = parser.parse_args()

    candles = download_ohlcv(args.exchange, args.symbol, args.timeframe, args.limit)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    candles.to_csv(output, index=False)
    print(f"Saved {len(candles)} candles to {output}")
    print(f"Range: {candles.timestamp.iloc[0]} -> {candles.timestamp.iloc[-1]}")
    print("Public market data only. No API keys or orders used.")


if __name__ == "__main__":
    main()
