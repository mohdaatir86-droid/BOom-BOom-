# BOom-Boom Crypto Bot

Safety-first crypto research scaffold. Current mode: **backtesting/paper signals only**. No live exchange orders are implemented.

## What's in this repository
- OHLCV validation and EMA/RSI/ATR indicators
- Long-only baseline signal hypothesis (not a proven profitable strategy)
- Risk-based position sizing helper and daily realized-loss guard
- Simplified backtester with illustrative fee/slippage assumptions
- Unit tests for core risk helpers
- Trading-book principles in `docs/BOOK_KNOWLEDGE.md`

## Setup
Python 3.10+:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
python -m bot.backtest --csv path/to/ohlcv.csv --equity 10000
python -m bot.signal --csv path/to/ohlcv.csv
```
Windows activation: `.venv\\Scripts\\activate`.

CSV columns: `timestamp,open,high,low,close,volume`, strictly chronological, with valid positive OHLC prices. Timestamps should parse as dates. Do not use synthetic data to judge strategy performance.

## Important limitations
- No exchange connection or real-money order placement.
- The daily loss guard is a helper and is not yet wired into backtest/order orchestration.
- Backtest execution assumptions are simplified; funding, exchange-specific fees, partial fills, gaps and liquidation are not fully modelled.
- This is not proof of a profitable edge. Do not deploy to live trading based on these results.
- Before live trading: add reliable exchange data, venue-specific costs/funding, chronological out-of-sample and walk-forward tests, robust order reconciliation, monitoring, hard exposure/drawdown controls, and independently tested emergency stop.
- Store secrets only in environment/secret management; never commit API keys.
