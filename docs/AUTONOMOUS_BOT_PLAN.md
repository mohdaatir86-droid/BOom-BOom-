# BOom Boom — Autonomous Crypto Futures Roadmap

## User requirements
- Market: crypto.
- Intended venue/product: Binance Futures.
- Initial capital range discussed: ₹50,000–₹2,00,000.
- User wants a highly autonomous system, predictions, and automated operation.
- Priority: capital protection and evidence of positive net expectancy after fees, slippage and funding.
- The earlier 99% accuracy goal is an aspiration, not a realistic promise or acceptance criterion. We will measure calibration, net expectancy, drawdown and robustness rather than optimize raw accuracy.

## Non-negotiable safety
- Current repository is research/backtest/paper-only; no live order placement.
- Never request or commit exchange secrets in chat or Git.
- For eventual Binance access, use a dedicated API key with withdrawals disabled, minimal permissions, IP allowlisting where possible, and initially no trading permission. Only add futures trading permission after paper and risk gates pass.
- Futures involve liquidation and funding risk. Leverage is not a profit multiplier without additional risk; start with no leverage or the lowest feasible exposure in simulation.
- Fail closed on stale/malformed data, unhandled exceptions, unknown position state, exchange mismatch, and loss-limit breaches.
- Hard kill switch and reconciliation must exist before any live execution.
- Never promise returns. The system must be allowed to decide NO TRADE.

## Phased delivery
### Phase 1 — Foundation and book-to-code mapping
- Maintain a book-to-code matrix for Mark Douglas, Alexander Elder, Steve Nison and Van K. Tharp.
- Convert relevant concepts to code and tests, separating source-derived ideas from model-added engineering safeguards.
- Validate all pattern definitions and prevent look-ahead leakage.
- CI must pass for supported Python versions.

### Phase 2 — Market data and research dataset
- Download and store historical Binance futures candles for multiple liquid pairs and timeframes.
- Add funding-rate and open-interest history where accessible; document missing fields rather than fabricating them.
- Store immutable timestamped data and data-quality checks; exclude incomplete current candles from signals.
- Record dataset ranges and provenance for each experiment.

### Phase 3 — Baseline and realistic backtest
- Repair the research backtester before trusting metrics: gap-through-stop handling, signal timing, position sizing, fees, spread/slippage, funding, futures contract rules, and drawdown marking.
- Add chronological train/validation/test splits, walk-forward tests, multiple market regimes and parameter sensitivity checks.
- Report trade count, expectancy in R, net expectancy after costs, profit factor, maximum drawdown, turnover, exposure, losing streak, and uncertainty.
- Compare against buy/hold and simple baselines. Reject strategies that do not beat costs and risk-adjusted baselines out of sample.

### Phase 4 — Prediction and decision engine
- Start with transparent rule-based features and calibrated statistical baselines before complex ML.
- Features may include trend, momentum, candle context, volume, volatility/regime, funding, open interest, order-book imbalance and news only when reliable timestamped data is available.
- Define a target precisely (e.g. probability that a trade reaches +R before -1R within a fixed horizon); never label model output as certainty.
- Use time-series splits only, probability calibration, leakage checks, drift detection and model versioning.
- Separate prediction from decision: only trade when estimated edge exceeds all costs and risk constraints.

### Phase 5 — Paper automation
- Scheduled market data collection, signal generation, simulated orders, stop/target lifecycle, funding/cost accounting, trade journal, health checks, alerts and kill switch.
- Test restart recovery, duplicate signals, missing candles, rate limits, network failures and exchange position reconciliation.
- Require a meaningful period of stable paper operation and predefined acceptance thresholds before live consideration.

### Phase 6 — Limited live execution (not enabled)
- Only after user review of test evidence and explicit authorization.
- Use a separate low-balance account/subaccount if available; withdrawals disabled, minimal API permissions, IP restriction and environment secrets.
- Strict caps on notional, leverage, per-trade risk, daily loss, total drawdown and concurrent positions.
- Emergency kill switch cancels entry orders and stops new entries; exits/reconciliation must be designed and tested carefully.
- Monitor continuously and automatically halt on breached thresholds.

## Current implementation status (do not overstate)
- Public read-only OHLCV download via CCXT: added.
- EMA/RSI/ATR baseline and a simplified long-only strategy: added, unproven.
- Risk sizing helper and daily realized-loss helper: added; risk guard is not yet wired into full orchestration.
- Basic simplified backtester: added; not yet adequate for futures performance claims.
- Initial candlestick feature approximations and tests: added; CI result must be checked and definitions reviewed.
- Book notes and book-to-code matrix: added.
- Live Binance Futures execution, prediction probability model, funding-aware backtest, paper execution engine, dashboard/alerts, portfolio-level controls: pending.

## Required user access (only when a phase needs it)
1. Public market data can be fetched without user credentials.
2. For private account/balance read-only testing later: create a dedicated Binance API key with read-only permissions, withdrawals disabled; put it directly into deployment secret storage, never chat or repository.
3. For live futures orders, do not grant trading permission until all prior safety gates pass and user explicitly authorizes that phase.
4. If deployment is needed, provide access to the chosen hosting account through its supported secure integration, not passwords pasted into chat.

## Success criteria
Success is not 99% directional accuracy. It is a reproducible, sufficiently large out-of-sample sample with positive net expectancy after realistic costs, acceptable drawdown, calibrated probabilities, stable paper results, and reliable failure handling. If evidence fails, the bot should remain paper-only.
