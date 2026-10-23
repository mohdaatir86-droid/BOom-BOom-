"""Read-only public USD-M futures market data via CCXT; no order methods are called."""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
from .data import normalize_ohlcv


def normalize_funding_rates(rows) -> pd.DataFrame:
    """Normalize CCXT funding-history records to timestamp, symbol and funding_rate."""
    if not rows:
        return pd.DataFrame(columns=["timestamp", "symbol", "funding_rate"])
    records = []
    for item in rows:
        timestamp = item.get("timestamp")
        rate = item.get("fundingRate")
        if timestamp is None or rate is None:
            info = item.get("info") or {}
            timestamp = timestamp if timestamp is not None else info.get("fundingTime")
            rate = rate if rate is not None else info.get("fundingRate")
        if timestamp is None or rate is None:
            continue
        ts = pd.to_datetime(timestamp, unit="ms", utc=True, errors="coerce")
        try:
            value = float(rate)
        except (TypeError, ValueError):
            continue
        if pd.isna(ts) or not pd.notna(value) or abs(value) == float("inf"):
            continue
        records.append({"timestamp": ts, "symbol": item.get("symbol"), "funding_rate": value})
    df = pd.DataFrame(records, columns=["timestamp", "symbol", "funding_rate"])
    if df.empty:
        return df
    return df.drop_duplicates(["timestamp", "symbol"], keep="last").sort_values("timestamp").reset_index(drop=True)


def create_futures_exchange(exchange_id="binanceusdm"):
    import ccxt
    exchange_class = getattr(ccxt, exchange_id, None)
    if exchange_class is None or not callable(exchange_class):
        raise ValueError(f"Unsupported CCXT exchange: {exchange_id}")
    exchange = exchange_class({"enableRateLimit": True})
    if not exchange.has.get("fetchOHLCV"):
        raise ValueError(f"{exchange_id} does not support OHLCV through CCXT")
    return exchange


def download_futures_dataset(symbol="BTC/USDT", timeframe="1h", limit=1000, exchange_id="binanceusdm"):
    """Download recent USD-M futures candles and available funding history."""
    if not isinstance(limit, int) or not 2 <= limit <= 1500:
        raise ValueError("limit must be an integer between 2 and 1500")
    exchange = create_futures_exchange(exchange_id)
    exchange.load_markets()
    if symbol not in exchange.markets:
        raise ValueError(f"Symbol {symbol!r} is not listed on {exchange_id}")
    candles = normalize_ohlcv(exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit))
    funding = pd.DataFrame(columns=["timestamp", "symbol", "funding_rate"])
    if exchange.has.get("fetchFundingRateHistory"):
        since = int(candles["timestamp"].iloc[0].timestamp() * 1000)
        try:
            rates = exchange.fetch_funding_rate_history(symbol, since=since, limit=1000)
            funding = normalize_funding_rates(rates)
            if not funding.empty:
                start = candles["timestamp"].iloc[0]
                end = candles["timestamp"].iloc[-1]
                funding = funding[(funding.timestamp >= start) & (funding.timestamp <= end)].reset_index(drop=True)
        except (NotImplementedError, Exception) as exc:
            # Keep the candle dataset usable, but make missing funding explicit.
            funding.attrs["warning"] = f"Funding history unavailable: {type(exc).__name__}: {exc}"
    return candles, funding


def main():
    parser = argparse.ArgumentParser(description="Download public Binance USD-M futures candles and funding history.")
    parser.add_argument("--exchange", default="binanceusdm")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--out", default="data/BTC_USDT_PERP_1h.csv")
    parser.add_argument("--funding-out", default="data/BTC_USDT_funding.csv")
    args = parser.parse_args()
    candles, funding = download_futures_dataset(args.symbol, args.timeframe, args.limit, args.exchange)
    out, funding_out = Path(args.out), Path(args.funding_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    funding_out.parent.mkdir(parents=True, exist_ok=True)
    candles.to_csv(out, index=False)
    funding.to_csv(funding_out, index=False)
    print(f"Saved {len(candles)} futures candles to {out}")
    print(f"Saved {len(funding)} funding records to {funding_out}")
    if funding.empty:
        print("WARNING: funding history is empty; do not treat futures backtest as funding-complete.")
    print("Public data only. No API keys or orders used.")


if __name__ == "__main__":
    main()
