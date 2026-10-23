# Research data and validation

## Open interest
Download recent public Binance USD-M open-interest history:
```bash
python -m bot.open_interest --symbol BTCUSDT --period 1h --limit 500 --out data/BTC_USDT_open_interest.csv
```
The public endpoint has bounded recent history and exchange rate limits. Do not treat missing data as zero. Open interest is not yet joined into the baseline strategy or model.

## Chronological holdout
```python
import pandas as pd
from bot.validation import chronological_split
candles = pd.read_csv("data/BTC_USDT_PERP_1h.csv")
train, validation, test = chronological_split(candles)
```
This splits rows in time order; it does not train a model or automatically evaluate strategy performance. Never shuffle time-series data. Any indicator warm-up and labels that span time boundaries need embargo/purge treatment before model evaluation.

## Walk-forward windows
Use `walk_forward_windows(df, train_size, test_size, step_size)` for rolling chronological train/test windows. This utility only creates windows. Strategy parameters must be selected using the training window only; test windows are for evaluation and must not be used to tune the same run.

## Research gates
- Keep incomplete current candles out of final evaluation.
- Ensure all features were available at the timestamp of the decision.
- Track source, timezone, symbol, timeframe, and data range.
- Include realistic fees, slippage, funding, spread and contract rules.
- Report enough trades and multiple market regimes; never use raw accuracy as the only objective.
- Do not claim positive expectancy until it is replicated out-of-sample and after costs.
