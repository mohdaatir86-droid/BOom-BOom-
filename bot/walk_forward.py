"""Leakage-aware rolling out-of-sample evaluation for the baseline strategy."""
from __future__ import annotations

import argparse
import json
import pandas as pd

from .backtest import run_backtest
from .config import BotConfig
from .metrics import summarize_trades
from .validation import walk_forward_windows


def evaluate_walk_forward(
    candles: pd.DataFrame,
    config: BotConfig | None = None,
    train_size: int = 500,
    test_size: int = 100,
    step_size: int | None = None,
    funding_df: pd.DataFrame | None = None,
    funding_mark_price_column: str | None = None,
) -> dict:
    """Score only test-period entries while retaining prior candles for indicator warm-up.

    Each fold starts with fresh initial equity (no equity carry-over). Returns and
    drawdowns are therefore per-fold, not cumulative portfolio results. Only trades
    whose entry_time falls inside the held-out test window are aggregated into the
    out-of-sample metrics. Funding events are restricted to the same test window
    (including fold start). Signals on the final warm-up candle may trigger an entry
    at the first test candle's open (point-in-time valid). This is a baseline
    diagnostic, not parameter optimization or a futures execution simulator.
    """
    if "timestamp" not in candles.columns:
        raise ValueError("timestamp column is required")
    ts = pd.to_datetime(candles["timestamp"], utc=True, errors="coerce")
    if ts.isna().any() or not ts.is_monotonic_increasing or ts.duplicated().any():
        raise ValueError("Timestamps must be valid, unique and chronological")
    folds = []
    all_test_trades = []
    for index, (warmup, test) in enumerate(
        walk_forward_windows(candles, train_size, test_size, step_size), start=1
    ):
        segment = pd.concat([warmup, test], ignore_index=True)
        start = pd.to_datetime(test.iloc[0]["timestamp"], utc=True)
        end = pd.to_datetime(test.iloc[-1]["timestamp"], utc=True)
        funding = funding_df
        if funding is not None and not funding.empty:
            funding_times = pd.to_datetime(funding["timestamp"], utc=True, errors="coerce")
            # Include funding at fold start so an entry at the first test open can receive it.
            funding = funding.loc[(funding_times >= start) & (funding_times <= end)].copy()
        result = run_backtest(
            segment,
            config or BotConfig(),
            funding_df=funding,
            funding_mark_price_column=funding_mark_price_column,
            trade_start_time=start,
        )
        test_trades = [
            trade for trade in result["trades_detail"]
            if pd.to_datetime(trade["entry_time"], utc=True) >= start
        ]
        all_test_trades.extend(test_trades)
        folds.append({
            "fold": index,
            "test_start": start.isoformat(),
            "test_end": end.isoformat(),
            "test_candles": int(len(test)),
            "trade_count": len(test_trades),
            "net_pnl": round(sum(float(t["pnl_net"]) for t in test_trades), 4),
        })
    metrics = summarize_trades(all_test_trades, (config or BotConfig()).initial_equity)
    return {
        "mode": "WALK_FORWARD_OUT_OF_SAMPLE",
        "folds": folds,
        "fold_count": len(folds),
        "out_of_sample_trade_count": metrics["trade_count"],
        "out_of_sample_net_pnl": metrics["net_pnl"],
        "out_of_sample_win_rate_pct": metrics["win_rate_pct"],
        "out_of_sample_profit_factor": metrics["profit_factor"],
        "out_of_sample_expectancy_per_trade": metrics["expectancy_per_trade"],
        "warning": "Out-of-sample historical evaluation only; not evidence of future profitability or live execution readiness.",
    }



def main():
    parser = argparse.ArgumentParser(description="Run rolling out-of-sample backtest folds.")
    parser.add_argument("--csv", required=True, help="Chronological OHLCV CSV")
    parser.add_argument("--funding-csv", help="Optional funding history CSV")
    parser.add_argument("--equity", type=float, default=10000.0)
    parser.add_argument("--train-size", type=int, default=500, help="Prior candles retained for indicator warm-up")
    parser.add_argument("--test-size", type=int, default=100, help="Candles scored in each out-of-sample fold")
    parser.add_argument("--step-size", type=int, help="Fold advance; defaults to test-size")
    parser.add_argument("--funding-mark-price-column", help="Optional mark-price column in funding CSV")
    args = parser.parse_args()
    funding = pd.read_csv(args.funding_csv) if args.funding_csv else None
    result = evaluate_walk_forward(
        pd.read_csv(args.csv),
        BotConfig(initial_equity=args.equity),
        train_size=args.train_size,
        test_size=args.test_size,
        step_size=args.step_size,
        funding_df=funding,
        funding_mark_price_column=args.funding_mark_price_column,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
