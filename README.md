# BOom-Boom Crypto Bot

Safety-first crypto research scaffold. Current mode: **backtesting/paper signals only**. No live exchange orders are implemented.

## What's in this repository
- Read-only public spot OHLCV downloader via CCXT (no API keys needed)
- Read-only USD-M futures candle and available funding-history downloader
- Public Binance open-interest history downloader
- Chronological holdout and walk-forward window utilities
- OHLCV validation and EMA/RSI/ATR indicators
- Long-only baseline signal hypothesis (not a proven profitable strategy)
- Risk-based position sizing helper and daily realized-loss guard
- Simplified backtester with illustrative fee/slippage assumptions, optional funding adjustment and expectancy/R metrics
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
python -m bot.open_interest --symbol BTCUSDT --period 1h --limit 500 --out data/BTC_USDT_open_interest.csv
python -m bot.backtest --csv data/BTC_USDT_1h.csv --equity 10000
python -m bot.walk_forward --csv data/BTC_USDT_1h.csv --train-size 500 --test-size 100 --equity 10000
python -m bot.backtest --csv data/BTC_USDT_PERP_1h.csv --funding-csv data/BTC_USDT_funding.csv --equity 10000
python -m bot.signal --csv data/BTC_USDT_1h.csv
python -m bot.paper --csv data/BTC_USDT_1h.csv --journal data/paper_journal.jsonl
python -m bot.paper --csv data/BTC_USDT_1h.csv --simulate --state data/paper_state.json --trade-journal data/paper_trades.jsonl
```
Windows activation: `.venv\\Scripts\\activate`.

CSV columns: `timestamp,open,high,low,close,volume`, strictly chronological, with valid positive OHLC prices. Timestamps should parse as dates. The downloader fetches recent public candles; the latest candle may still be incomplete. For research, remove incomplete candles and collect enough history. Do not use synthetic data to judge strategy performance.

## Important limitations
- No exchange connection or real-money order placement.
- The daily-loss guard is applied in the simplified backtest and offline paper simulator. `bot.paper` defaults to signal journaling; pass `--simulate` for offline simulated fills and persistent state. This is not an exchange-connected execution engine.
- Backtest execution assumptions are simplified; funding is applied at event timestamps, using an optional supplied mark-price column or previous candle close as a disclosed proxy. Exchange-specific tick/lot rules, partial fills, spread, margin tiers and liquidation are not fully modelled.
- This is not proof of a profitable edge. Do not deploy to live trading based on these results.
- Before live trading: add reliable exchange data, venue-specific costs/funding, chronological out-of-sample and walk-forward tests, robust order reconciliation, monitoring, hard exposure/drawdown controls, and independently tested emergency stop.
- Store secrets only in environment/secret management; never commit API keys.

## Point-in-time open-interest features

Align public open-interest snapshots to candles without look-ahead bias:

```python
from bot.market_features import align_open_interest
features = align_open_interest(candles, open_interest, tolerance="2h")
```

This backward-only timestamp join prevents future OI records from being attached to earlier candles. See [`docs/OPEN_INTEREST_FEATURES.md`](docs/OPEN_INTEREST_FEATURES.md) for caveats and example details. The feature is not yet a validated trading signal.

### Walk-forward evaluation options

The repository currently exposes two research interfaces:

- Rolling train/test windows: `python -m bot.walk_forward --csv data/BTC_USDT_1h.csv --train-size 500 --test-size 100 --equity 10000`
- Expanding-history folds: call `walk_forward_evaluate(...)` from `bot.backtest` in Python. Each fold resets to initial equity and reports fold-level metrics.

These are separate diagnostic views, not a combined live-equity simulation. Compare held-out trade counts and fold boundaries carefully; neither interface proves future profitability.

Backtest verification checklist: [`docs/BACKTEST_VERIFICATION_GATES.md`](docs/BACKTEST_VERIFICATION_GATES.md). This lists unresolved simulator requirements and prevents CI success from being mistaken for evidence of profitability.
