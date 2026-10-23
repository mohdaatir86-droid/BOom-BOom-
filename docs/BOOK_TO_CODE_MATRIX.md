# BOom Boom — Book-to-Code Implementation Matrix

This is an original, concise engineering synthesis of the uploaded trading books, not a reproduction of their text. A concept is not implemented merely because it appears in documentation: it needs code, tests, and measurable validation.

Status: Implemented (partial) means a basic mechanism exists; Added now means code added, CI pending; Pending means not built; Validation required means code exists but its performance benefit is unproven.

## 1. Mark Douglas — Trading in the Zone
- Treat each setup as a probability distribution, not certainty — partial: baseline signals are hypotheses; per-setup outcome statistics pending.
- Think in series of trades rather than judging one trade — partial: aggregate backtest metrics exist.
- Accept risk before entry; do not expand risk after losses — pending: immutable risk budget and loss-streak cooldown.
- Execute rules consistently; avoid discretionary override — pending: formal rule checklist and auditable decision log.
- Separate process quality from a single winning/losing outcome — pending: planned-vs-actual execution review.
- Build confidence from evidence, not prediction — pending: out-of-sample and walk-forward acceptance gates.

## 2. Alexander Elder — The New Trading for a Living
- Define plan, entry, exit and risk before a trade — partial: stop/target and sizing helpers exist; orchestration incomplete.
- Use indicators as tools within a system, not isolated magic signals — partial: EMA/RSI/ATR baseline.
- Keep records and review mistakes — pending: persistent journal and review reports.
- Control risk and position size — partial: sizing helper; venue limits and portfolio exposure pending.
- Account for execution costs — partial: illustrative fees/slippage; spread, funding, partial fills and gaps pending.

## 3. Steve Nison — Japanese Candlestick Charting Techniques
- Read candle bodies, shadows and range as context — added now: doji, hammer, shooting star, bullish/bearish engulfing, and mechanical morning/evening-star approximations in bot/candles.py.
- Interpret patterns in context, not as standalone commands — pending: trend/location/volume filters and pattern-specific outcome studies.
- Validate definitions and thresholds on crypto data/timeframes — pending.
- Patterns fail; stops and position sizing remain necessary — partial: helpers exist; strategy integration and validation pending.
- The three-candle star rules in the initial code are approximations and require review against exact source descriptions.

## 4. Van K. Tharp — Trade Your Way to Financial Freedom
- Define objectives and system constraints — pending: configurable objectives and drawdown limits.
- Measure expectancy and R-multiples — partial: profit factor/win rate/net PnL; expectancy in R pending.
- Size by risk and stop distance — partial: linear spot-like sizing; venue filters, fees, gaps and portfolio exposure pending.
- Evaluate enough trades and varied market regimes — pending: sample sufficiency, regime segmentation, bootstrap/Monte Carlo, walk-forward.
- Avoid optimising only to historical data — pending: chronological train/validation/test and leakage controls.

## 5. Ernest P. Chan — Machine Trading (supplementary)
The full text was not verified page-by-page. These are general quantitative safeguards, not a complete extraction of that book:
- Realistic costs and no look-ahead bias — partial.
- Out-of-sample validation and performance-decay monitoring — pending.
- Data/source quality and reproducible experiments — pending.

## Additional engineering safeguards (model-added, not attributed to the books)
- Never commit exchange secrets.
- Keep first iteration read-only and paper-only.
- Fail closed on invalid or stale data and uncertain risk state.
- Test order idempotency/reconciliation before live execution.
- Require hard kill switch, exposure/drawdown limits before live trading.
- Record code version, config, data window and costs for every backtest.
- Never promote a strategy from one backtest or win rate alone.

## Acceptance checklist before live trading
1. Unit tests pass across supported Python versions.
2. Pattern definitions have focused tests and independent review.
3. Integrate candle features only without look-ahead leakage.
4. Include venue fees, spread, slippage, funding, lot/tick/min-notional rules and gap risk.
5. Use chronological holdouts and walk-forward evaluation.
6. Report expectancy in R, net expectancy, profit factor, drawdown, return, exposure, turnover, trade count and uncertainty.
7. Paper trade with fill reconciliation and alerts for a meaningful period.
8. Keep live execution disabled until all gates are reviewed.

## Copyright and source fidelity
This file paraphrases concepts and maps them to software tasks; it does not reproduce the books. Earlier review did not verify every page of every book. Revisit actual uploaded source files chapter-by-chapter to improve completeness and record page/chapter references internally.
