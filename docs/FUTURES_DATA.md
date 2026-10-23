# Futures market data

## Download
```bash
python -m bot.futures_data --exchange binanceusdm --symbol BTC/USDT --timeframe 1h --limit 1000 --out data/BTC_USDT_PERP_1h.csv --funding-out data/BTC_USDT_funding.csv
```

This uses public CCXT endpoints only. No API key, account access, or order endpoint is used.

## Files
- Candle CSV: `timestamp,open,high,low,close,volume` with UTC timestamps.
- Funding CSV: `timestamp,symbol,funding_rate`.

## Current limitations
- The command fetches a recent window (up to 1500 candles), not full multi-year history.
- Funding endpoint history coverage/rate limits vary by venue and CCXT version. An empty funding file is a warning, not proof that funding was zero.
- The current candle may be incomplete; exclude it from final research runs.
- Open interest history is not included yet.
- Do not infer funding cost by multiplying a single latest funding rate over all periods. Funding must be joined to positions at actual funding timestamps and directionally accounted for in the backtester.
- This data adapter does not trade or read private account data.


## Funding cost research helper

`bot/funding.py` estimates funding PnL for already-recorded long trades using actual funding timestamps. By default it uses entry price as a proxy for mark price; this is approximate, not venue-exact. If mark-price observations are available, pass a `mark_price` column and set `mark_price_column="mark_price"`. This helper is not yet integrated into the main backtest equity curve, so do not interpret the existing backtest metrics as funding-adjusted.
