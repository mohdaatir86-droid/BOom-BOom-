# Out-of-sample evaluation snapshot (2026-10-23)

**Not proof of profitability.** Baseline long-only EMA/RSI/ATR hypothesis only.

## Data

| Field | Value |
|-------|--------|
| Venue | OKX public API (`BTC-USDT-SWAP`, `ETH-USDT-SWAP`) |
| Why not Binance | `fapi.binance.com` returned HTTP 451 (geo-restricted) from the evaluation host |
| Timeframe | 1h |
| Candle range | 2026-09-12 04:00 UTC → 2026-10-23 18:00 UTC (999 bars after dropping incomplete last bar) |
| Funding | 286 events per symbol (OKX funding-rate history) |
| Costs | fee_rate=0.0006, slippage_rate=0.0005, risk_per_trade=0.0025, initial_equity=10000 |

Reproduce:

```bash
# Download from an unrestricted network (Binance preferred if available):
python -m bot.futures_data --exchange binanceusdm --symbol BTC/USDT --timeframe 1h --limit 1000 \
  --out data/BTC_USDT_PERP_1h.csv --funding-out data/BTC_USDT_funding.csv
python -m bot.walk_forward --csv data/BTC_USDT_PERP_1h.csv --funding-csv data/BTC_USDT_funding.csv \
  --train-size 500 --test-size 100 --equity 10000
```

## Single-period backtest (includes funding)

| Metric | BTC | ETH |
|--------|-----|-----|
| Net PnL | −148.58 (−1.49%) | −156.66 (−1.57%) |
| Trades | 26 | 22 |
| Win rate | 30.8% | 27.3% |
| Profit factor | 0.66 | 0.60 |
| Expectancy / trade | −5.71 | −7.12 |
| Max drawdown | 2.58% | 2.78% |
| Max consecutive losses | 6 | 5 |

## Rolling walk-forward (train=500, test=100, step=100; equity reset each fold)

| Metric | BTC | ETH |
|--------|-----|-----|
| Folds | 5 | 5 |
| OOS trades | 14 | 11 |
| OOS net PnL | −140.10 | −150.13 |
| OOS win rate | 21.4% | 18.2% |
| OOS profit factor | 0.41 | 0.31 |
| OOS expectancy | −10.01 | −13.65 |

## Limitations

- Short sample (~6 weeks); not statistically robust.
- OKX perps, not Binance USD-M; funding and microstructure differ.
- Simplified fills (OHLCV stop/target, previous-close funding mark proxy).
- No claim of future performance. Live order placement is not implemented.
