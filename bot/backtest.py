import argparse
import pandas as pd
from .config import BotConfig
from .indicators import validate_ohlcv
from .strategy import generate_signals
from .risk import position_size, validate_long_trade, RiskState
from .funding import apply_funding_to_trades
from .metrics import equity_curve, summarize_trades


def run_backtest(df, config=None, funding_df=None):
    """Simplified long-only research backtest; optional funding is post-applied to trade PnL."""
    cfg = config or BotConfig()
    validate_ohlcv(df)
    data = generate_signals(df, cfg).reset_index(drop=True)
    equity = float(cfg.initial_equity)
    position = None
    trades = []
    risk_state = RiskState(start_of_day_equity=equity)
    active_day = None

    for i in range(1, len(data)):
        row, prev = data.iloc[i], data.iloc[i - 1]
        bar_time = pd.to_datetime(row["timestamp"], utc=True, errors="coerce")
        if pd.isna(bar_time):
            raise ValueError("Backtest timestamps must be valid")
        bar_day = bar_time.date()
        if active_day != bar_day:
            active_day = bar_day
            risk_state = RiskState(start_of_day_equity=equity)
        exited_this_bar = False
        if position:
            exit_price, reason = None, ""
            # Conservative intrabar ordering: if both touched, assume stop first.
            if row["low"] <= position["stop"]:
                exit_price, reason = position["stop"], "stop"
            elif row["high"] >= position["target"]:
                exit_price, reason = position["target"], "target"
            if exit_price is not None:
                fill = float(exit_price) * (1 - cfg.slippage_rate)
                fees = position["qty"] * (position["entry"] + fill) * cfg.fee_rate
                pnl = position["qty"] * (fill - position["entry"]) - fees
                equity += pnl
                risk_state.record_realized_pnl(pnl, cfg.daily_loss_limit)
                trades.append({
                    "entry_time": position["time"], "exit_time": row["timestamp"],
                    "entry": position["entry"], "exit": fill, "qty": position["qty"],
                    "initial_risk": position["initial_risk"], "pnl_net": pnl, "reason": reason,
                })
                position = None
                exited_this_bar = True

        # Signal is from completed prior candle; entry occurs at current open.
        if position is None and not exited_this_bar and risk_state.can_open_new_position() and bool(prev["long_signal"]):
            entry = float(row["open"]) * (1 + cfg.slippage_rate)
            atr = float(prev["atr"])
            if pd.isna(atr) or atr <= 0:
                continue
            stop = entry - cfg.stop_atr_multiple * atr
            target = entry + 2 * (entry - stop)
            if not validate_long_trade(entry, stop, target):
                continue
            cost_per_unit = entry * (2 * cfg.fee_rate + 2 * cfg.slippage_rate)
            qty = position_size(equity, entry, stop, cfg.risk_per_trade, cost_per_unit)
            if qty > 0:
                position = {
                    "time": row["timestamp"], "entry": entry, "stop": stop,
                    "target": target, "qty": qty, "initial_risk": qty * (entry - stop),
                }

    if position is not None and len(data):
        last = float(data.iloc[-1]["close"]) * (1 - cfg.slippage_rate)
        fees = position["qty"] * (position["entry"] + last) * cfg.fee_rate
        pnl = position["qty"] * (last - position["entry"]) - fees
        trades.append({
            "entry_time": position["time"], "exit_time": data.iloc[-1]["timestamp"],
            "entry": position["entry"], "exit": last, "qty": position["qty"],
            "initial_risk": position["initial_risk"], "pnl_net": pnl, "reason": "end_of_data",
        })

    funding_warning = None
    if funding_df is not None:
        if funding_df.empty:
            funding_warning = "Funding CSV is empty; funding adjustment is zero only because no records were supplied, not because funding was zero."
        else:
            trades = apply_funding_to_trades(trades, funding_df)
            for trade in trades:
                trade["pnl_net_before_funding"] = float(trade["pnl_net"])
                # Keep reported metrics and equity consistent with estimated funding PnL.
                trade["pnl_net"] = float(trade["pnl_net_after_funding_estimate"])
            funding_warning = "Funding estimated using entry-price proxy; summary metrics include estimated funding. Use mark-price observations for more accurate estimates."

    metrics = summarize_trades(trades, cfg.initial_equity)
    curve = equity_curve(trades, cfg.initial_equity)
    final_equity = float(curve.iloc[-1]["equity"])
    max_drawdown = float(curve["drawdown_pct"].max()) if len(curve) else 0.0
    return {
        "initial_equity": cfg.initial_equity,
        "final_equity": round(final_equity, 2),
        "net_pnl": round(final_equity - cfg.initial_equity, 2),
        "return_pct": round((final_equity / cfg.initial_equity - 1) * 100, 3),
        "trades": metrics["trade_count"],
        "win_rate_pct": metrics["win_rate_pct"],
        "profit_factor": metrics["profit_factor"],
        "expectancy_per_trade": metrics["expectancy_per_trade"],
        "expectancy_r": metrics["expectancy_r"],
        "max_consecutive_losses": metrics["max_consecutive_losses"],
        "max_drawdown_pct": round(max_drawdown, 3),
        "funding_adjusted": funding_df is not None and not funding_df.empty,
        "funding_warning": funding_warning,
        "trades_detail": trades,
        "warning": "Simplified research backtest, not a futures-execution simulator and not proof of live profitability.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--funding-csv", help="Optional funding history CSV from bot.futures_data")
    parser.add_argument("--equity", type=float, default=10000)
    args = parser.parse_args()
    funding = pd.read_csv(args.funding_csv) if args.funding_csv else None
    result = run_backtest(pd.read_csv(args.csv), BotConfig(initial_equity=args.equity), funding)
    for key, value in result.items():
        if key != "trades_detail":
            print(f"{key}: {value}")
    pd.DataFrame(result["trades_detail"]).to_csv("backtest_trades.csv", index=False)


if __name__ == "__main__":
    main()
