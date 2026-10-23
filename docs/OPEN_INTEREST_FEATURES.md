# Open-interest feature alignment

`bot.market_features.align_open_interest(candles, open_interest)` joins Binance
open-interest history to candle rows using a backward as-of join. Each candle
receives only the latest observation timestamped at or before that candle;
future snapshots are never used. Both timestamp columns are normalized to UTC,
and original candle row order is restored.

Example:

```python
from bot.market_features import align_open_interest
features = align_open_interest(candles, open_interest, tolerance="2h")
```

The optional tolerance prevents stale observations from being carried forward.
The output includes `open_interest`, `open_interest_value`, absolute change,
and percentage change. Initial changes remain null when there is no prior
matched observation.

Important limitations:
- Binance open-interest history is a recent, bounded public dataset, not a complete
  long-term archive.
- OI is a context feature, not a standalone directional signal.
- Timestamp alignment does not prove that a source's snapshot was available to a
  live strategy at that exact instant; add a conservative publication-delay buffer
  for production research.
- No API keys or order endpoints are used.
