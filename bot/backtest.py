import argparse
import pandas as pd
from .config import BotConfig
from .indicators import validate_ohlcv
from .strategy import generate_signals
from .risk import position_size, validate_long_trade, RiskState
from .funding import apply_funding_to_trades
from .metrics import equity_curve, summarize_trades


def run_backtest(df, config=None, funding_df=None, funding_mark_price_column=None, trade_start_time=None):
    """Simplified long-only research backtest; optional funding is post-applied to trade PnL."""
    cfg = config or BotConfig()
    validate_ohlcv(df)
    data = generate_signals(df, cfg).reset_index(drop=True)
    equity = float(cfg.initial_equity)
    position = None
    trades = []
    risk_state = RiskState(start_of_day_equity=equity)
    active_day = None
    funding_rows = []
    funding_index = 0
    funding_warning = None
    if funding_df is not None:
        required_funding = {"timestamp", "funding_rate"}
        if not required_funding.issubset(funding_df.columns):
            raise ValueError(f"funding must contain columns: {sorted(required_funding)}")
        if funding_df.empty:
            funding_warning = "Funding CSV is empty; funding is unknown, not confirmed zero."
        else:
            funding_rows = funding_df.copy()
            funding_rows["timestamp"] = pd.to_datetime(funding_rows["timestamp"], utc=True, errors="coerce")
            funding_rows["funding_rate"] = pd.to_numeric(funding_rows["funding_rate"], errors="coerce")
            if funding_rows[["timestamp", "funding_rate"]].isna().any().any():
                raise ValueError("Funding timestamps/rates contain invalid values")
            if funding_mark_price_column and funding_mark_price_column not in funding_rows.columns:
                raise ValueError(f"Missing mark-price column: {funding_mark_price_column}")
            if funding_mark_price_column:
                funding_rows[funding_mark_price_column] = pd.to_numeric(funding_rows[funding_mark_price_column], errors="coerce")
                if funding_rows[funding_mark_price_column].isna().any() or (funding_rows[funding_mark_price_column] <= 0).any():
                    raise ValueError("Funding mark prices must be valid and positive")
            funding_rows = funding_rows.sort_values("timestamp").reset_index(drop=True)
            if funding_rows["timestamp"].duplicated().any():
                raise ValueError("Funding timestamps must be unique")
    peak_marked_equity = equity
    max_marked_drawdown_pct = 0.0

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
        while funding_index < len(funding_rows) and funding_rows.iloc[funding_index]["timestamp"] <= bar_time:
            funding_row = funding_rows.iloc[funding_index]
            funding_index += 1
            if position is None or funding_row["timestamp"] <= pd.to_datetime(position["time"], utc=True):
                continue
            mark = float(funding_row[funding_mark_price_column]) if funding_mark_price_column else float(prev["close"])
            funding_pnl = -float(position["qty"]) * mark * float(funding_row["funding_rate"])
            equity += funding_pnl
            position["funding_pnl"] = float(position.get("funding_pnl", 0.0)) + funding_pnl
            risk_state.record_realized_pnl(funding_pnl, cfg.daily_loss_limit)
        if position:
            exit_price, reason = None, ""
            # Conservative intrabar ordering: if both touched, assume stop first.
            if row["open"] <= position["stop"]:
                # If price gaps below the stop, assume an adverse open fill.
                exit_price, reason = float(row["open"]), "stop_gap"
            elif row["low"] <= position["stop"]:
                exit_price, reason = position["stop"], "stop"
            elif row["high"] >= position["target"]:
                exit_price, reason = position["target"], "target"
            if exit_price is not None:
                fill = float(exit_price) * (1 - cfg.slippage_rate)
                fees = position["qty"] * (position["entry"] + fill) * cfg.fee_rate
                pnl = position["qty"] * (fill - position["entry"]) - fees
                equity += pnl
                risk_state.record_realized_pnl(pnl, cfg.daily_loss_limit)
                funding_pnl = float(position.get("funding_pnl", 0.0))
                trades.append({
                    "entry_time": position["time"], "exit_time": row["timestamp"],
                    "entry": position["entry"], "exit": fill, "qty": position["qty"],
                    "initial_risk": position["initial_risk"], "pnl_net_before_funding": pnl,
                    "funding_pnl_estimate": funding_pnl, "pnl_net_after_funding_estimate": pnl + funding_pnl,
                    "pnl_net": pnl + funding_pnl, "reason": reason,
                })
                position = None
                exited_this_bar = True

        # Signal is from completed prior candle; entry occurs at current open.
        start_ok = trade_start_time is None or bar_time >= pd.to_datetime(trade_start_time, utc=True)
        if position is None and not exited_this_bar and start_ok and risk_state.can_open_new_position() and bool(prev["long_signal"]):
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
                    "target": target, "qty": qty, "initial_risk": qty * (entry - stop), "funding_pnl": 0.0,
                }

        # Track intra-trade equity troughs, including estimated exit costs.
        unrealized = 0.0
        if position is not None:
            mark = float(row["close"])
            unrealized = position["qty"] * (mark - position["entry"])
            unrealized -= position["qty"] * mark * (cfg.fee_rate + cfg.slippage_rate)
        # Enforce the daily loss guard on realized plus marked-to-market PnL.
        # This halts new entries; stop/target exits continue to be processed.
        risk_state.check_daily_loss(unrealized, cfg.daily_loss_limit)
        marked_equity = equity + unrealized
        peak_marked_equity = max(peak_marked_equity, marked_equity)
        if peak_marked_equity > 0:
            max_marked_drawdown_pct = max(
                max_marked_drawdown_pct,
                (peak_marked_equity - marked_equity) / peak_marked_equity * 100,
            )

    if position is not None and len(data):
        last = float(data.iloc[-1]["close"]) * (1 - cfg.slippage_rate)
        fees = position["qty"] * (position["entry"] + last) * cfg.fee_rate
        pnl = position["qty"] * (last - position["entry"]) - fees
        trades.append({
            "entry_time": position["time"], "exit_time": data.iloc[-1]["timestamp"],
            "entry": position["entry"], "exit": last, "qty": position["qty"],
            "initial_risk": position["initial_risk"], "pnl_net_before_funding": pnl,
            "funding_pnl_estimate": float(position.get("funding_pnl", 0.0)),
            "pnl_net_after_funding_estimate": pnl + float(position.get("funding_pnl", 0.0)),
            "pnl_net": pnl + float(position.get("funding_pnl", 0.0)), "reason": "end_of_data",
        })

    if funding_df is not None and not funding_df.empty:
        funding_warning = (
            "Funding applied at event time to equity and daily-loss checks. "
            + ("Supplied mark-price column used." if funding_mark_price_column else
               "Previous candle close used as a mark-price proxy between candle timestamps.")
        )

    metrics = summarize_trades(trades, cfg.initial_equity)
    curve = equity_curve(trades, cfg.initial_equity)
    final_equity = float(curve.iloc[-1]["equity"])
    realized_drawdown = float(curve["drawdown_pct"].max()) if len(curve) else 0.0
    max_drawdown = max(realized_drawdown, max_marked_drawdown_pct)
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
    parser.add_argument("--funding-mark-price-column", help="Optional mark-price column in funding CSV")
    args = parser.parse_args()
    funding = pd.read_csv(args.funding_csv) if args.funding_csv else None
    result = run_backtest(pd.read_csv(args.csv), BotConfig(initial_equity=args.equity), funding, args.funding_mark_price_column)
    for key, value in result.items():
        if key != "trades_detail":
            print(f"{key}: {value}")
    pd.DataFrame(result["trades_detail"]).to_csv("backtest_trades.csv", index=False)


if __name__ == "__main__":
    main()
