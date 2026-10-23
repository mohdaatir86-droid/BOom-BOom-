# Backtest verification gates

Before interpreting any strategy result as evidence, verify these cases in tests:

1. Funding is applied at event time to cash equity and daily-loss checks; trade metrics include it exactly once.
2. An empty funding file is reported as missing data, not zero funding observed.
3. A stop crossed by a candle opening gap is filled from the opening price (plus adverse slippage), not optimistically at the stop.
4. Daily realized loss limits halt new entries until the next UTC trading day; exits remain allowed.
5. An open position is marked to market for drawdown, not only after a trade closes.
6. The latest incomplete candle is excluded from any live-like signal evaluation.
7. Walk-forward evaluation computes features with prior warm-up history but scores only trades in the held-out test interval; folds are chronological and non-overlapping.
9. Both `bot.walk_forward.evaluate_walk_forward` (rolling train/test windows) and `bot.backtest.walk_forward_evaluate` (expanding-history folds) are research utilities; verify their outputs and avoid treating fold-reset equity as one continuous account.
8. Fees, slippage, funding, contract size, tick/lot sizes, and liquidation assumptions are recorded with every experiment.

Current limitations: funding marks use a supplied mark-price column or a previous-candle-close proxy; a funding timestamp inside a candle cannot be perfectly reconstructed from OHLCV alone. The strategy is an unproven long-only EMA/RSI hypothesis; the backtester is not a complete Binance Futures simulator. Passing unit tests validates implementation behavior, not profitability. No live orders should be enabled based on these checks alone.
