# Backtest verification gates

Before interpreting any strategy result as evidence, verify these cases. Each gate lists the primary automated test(s). Gates without a test are marked **unresolved**.

1. **Funding once, event-time** — Funding is applied at event time to cash equity and daily-loss checks; trade metrics include it exactly once.  
   Tests: `tests/test_funding_event_ledger.py`, `tests/test_backtest.py::test_funding_adjustment_is_reflected_in_final_equity`, `tests/test_backtest.py::test_accounting_reconciliation_funding_fees_slippage_eod`

2. **Empty funding is unknown** — An empty funding file is reported as missing data, not zero funding observed.  
   Test: `tests/test_backtest.py::test_empty_funding_csv_warns_unknown_not_zero`

3. **Stop-gap fill** — A stop crossed by a candle opening gap is filled from the opening price (plus adverse slippage), not optimistically at the stop.  
   Test: `tests/test_backtest.py::test_stop_gap_fills_at_open_not_stop`

4. **Daily loss limit** — Daily realized (and marked) loss limits halt new entries until the next UTC trading day; exits remain allowed.  
   Tests: `tests/test_risk.py::test_daily_loss_halts_entries`, `test_unrealized_daily_loss_halts_new_entries`, `test_realized_and_unrealized_loss_are_combined`

5. **Marked-to-market drawdown** — An open position is marked to market for drawdown, not only after a trade closes.  
   Test: `tests/test_backtest.py::test_marked_drawdown_tracks_open_position`

6. **Incomplete latest candle** — The latest incomplete candle is excluded from live-like signal evaluation.  
   Tests: `tests/test_paper.py::test_paper_signal_uses_last_completed_candle`, `test_paper_signal_requires_two_candles`

7. **Walk-forward held-out only** — Features use prior warm-up history; only trades in the held-out test interval are scored; folds are chronological and non-overlapping.  
   Tests: `tests/test_walk_forward.py`, `tests/test_backtest.py::test_walk_forward_uses_prior_history_but_gates_each_test_fold`, `test_evaluate_walk_forward_equity_reset_and_held_out_only`

8. **Cost assumptions recorded** — Fees, slippage, funding, and related assumptions are visible on each experiment (CLI/config/report fields).  
   Covered by backtest/walk-forward return payloads (`funding_warning`, fee/slippage in `BotConfig`). Full tick/lot/liquidation recording in the simplified OHLCV backtester remains **partial** (use `bot.binance_futures_simulator` separately).

9. **Two walk-forward interfaces** — `bot.walk_forward.evaluate_walk_forward` (rolling train/test) and `bot.backtest.walk_forward_evaluate` (expanding folds) both reset equity per fold; do not treat fold metrics as one continuous account.  
   Tests: as in gate 7; documented in README and module docstrings.

10. **Same-bar re-entry blocked** — A position that exits on a bar cannot re-enter on that same bar.  
    Test: `tests/test_backtest.py::test_backtest_does_not_reenter_on_same_bar_as_exit`

## Current limitations

- Funding marks use a supplied mark-price column or a previous-candle-close proxy; intra-candle funding timestamps cannot be reconstructed from OHLCV alone.
- The strategy is an unproven long-only EMA/RSI/ATR hypothesis.
- The OHLCV backtester is not a complete Binance Futures execution simulator.
- Passing unit tests validates implementation behavior, not profitability.
- No live orders should be enabled based on these checks alone.

See also: [docs/OOS_EVALUATION_2026-10.md](OOS_EVALUATION_2026-10.md) for a real chronological evaluation snapshot (negative OOS results).
