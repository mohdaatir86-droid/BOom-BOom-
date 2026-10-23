# BOom-Boom Crypto Bot

Safety-first crypto research scaffold. Current mode: **backtesting/paper signals only**. No live exchange orders are implemented.

## What's in this repository
- Read-only public spot OHLCV downloader via CCXT (no API keys needed)
- Read-only USD-M futures candle and available funding-history downloader
- OHLCV validation and EMA/RSI/ATR indicators
- Long-only baseline signal hypothesis (not a proven profitable strategy)
- Risk-based position sizing helper and daily realized-loss guard
- Simplified backtester with illustrative fee/slippage assumptions
- Candlestick feature flags with tests (research features, not standalone signals)
- Trade expectancy/R-multiple summary helpers and realized-equity curve
- Deterministic paper-signal journal; never places orders
- Unit tests for core risk helpers
- Trading-book principles in `docs/BOOK_KNOWLEDGE.md`

## Setup
Python 3.10+:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
python -m bot.data --exchange binance --symbol BTC/USDT --timeframe 1h --limit 500 --out data/BTC_USDT_1h.csv
python -m bot.futures_data --exchange binanceusdm --symbol BTC/USDT --timeframe 1h --limit 1000 --out data/BTC_USDT_PERP_1h.csv --funding-out data/BTC_USDT_funding.csv
python -m bot.backtest --csv data/BTC_USDT_1h.csv --equity 10000
python -m bot.signal --csv data/BTC_USDT_1h.csv
python -m bot.paper --csv data/BTC_USDT_1h.csv --journal data/paper_journal.jsonl
```
Windows activation: `.venv\\Scripts\\activate`.

CSV columns: `timestamp,open,high,low,close,volume`, strictly chronological, with valid positive OHLC prices. Timestamps should parse as dates. The downloader fetches recent public candles; the latest candle may still be incomplete. For research, remove incomplete candles and collect enough history. Do not use synthetic data to judge strategy performance.

## Important limitations
- No exchange connection or real-money order placement.
- The daily loss guard is a helper and is not yet wired into backtest/order orchestration. Paper journaling records signal snapshots only; it is not a full simulated fill/position engine.
- Backtest execution assumptions are simplified; futures funding data can now be downloaded but is not yet applied to PnL; exchange-specific fees, partial fills, gaps and liquidation are not fully modelled.
- This is not proof of a profitable edge. Do not deploy to live trading based on these results.
- Before live trading: add reliable exchange data, venue-specific costs/funding, chronological out-of-sample and walk-forward tests, robust order reconciliation, monitoring, hard exposure/drawdown controls, and independently tested emergency stop.
- Store secrets only in environment/secret management; never commit API keys.
