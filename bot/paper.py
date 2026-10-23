"""Deterministic paper signal journal. It never connects to an exchange or places orders."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
from .config import BotConfig
from .strategy import generate_signals


def evaluate_latest(csv_path: str, config: BotConfig | None = None) -> dict:
    data = pd.read_csv(csv_path)
    signals = generate_signals(data, config or BotConfig())
    if len(signals) < 2:
        raise ValueError("At least two candles are required to exclude the possibly incomplete latest candle")
    # The newest candle may still be forming; only journal the latest completed bar.
    row = signals.iloc[-2]
    return {
        "timestamp": str(row["timestamp"]),
        "close": float(row["close"]),
        "ema_fast": None if pd.isna(row["ema_fast"]) else float(row["ema_fast"]),
        "ema_slow": None if pd.isna(row["ema_slow"]) else float(row["ema_slow"]),
        "rsi": None if pd.isna(row["rsi"]) else float(row["rsi"]),
        "atr": None if pd.isna(row["atr"]) else float(row["atr"]),
        "long_signal": bool(row["long_signal"]),
        "mode": "PAPER_ONLY",
        "note": "Signal hypothesis only; no orders sent and no profitability claim.",
    }


def append_journal(result: dict, path: str = "data/paper_journal.jsonl") -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result, sort_keys=True) + "\n")


def run_paper_simulation(candles: pd.DataFrame, config: BotConfig | None = None,
                         state_path: str = "data/paper_state.json",
                         journal_path: str = "data/paper_trades.jsonl") -> dict:
    """Replay completed OHLCV bars through a persistent, offline-only simulated position."""
    from .risk import position_size, validate_long_trade, RiskState
    from .indicators import validate_ohlcv
    cfg = config or BotConfig()
    validate_ohlcv(candles)
    data = generate_signals(candles, cfg).reset_index(drop=True)
    state_file = Path(state_path)
    if state_file.exists():
        state = json.loads(state_file.read_text(encoding="utf-8"))
    else:
        state = {"equity": float(cfg.initial_equity), "position": None, "last_timestamp": None,
                 "realized_pnl_today": 0.0, "active_day": None, "halted": False}
    if state.get("position") is not None:
        state["position"] = dict(state["position"])
    events = []
    last_seen = state.get("last_timestamp")
    for i in range(1, len(data)):
        row, prev = data.iloc[i], data.iloc[i - 1]
        ts = pd.to_datetime(row["timestamp"], utc=True, errors="coerce")
        if pd.isna(ts):
            raise ValueError("paper simulation timestamps must be valid")
        iso = ts.isoformat()
        if last_seen and ts <= pd.to_datetime(last_seen, utc=True):
            continue
        day = ts.date().isoformat()
        if state.get("active_day") != day:
            state["active_day"], state["realized_pnl_today"], state["halted"] = day, 0.0, False
        pos = state.get("position")
        if pos:
            exit_px, reason = None, None
            if float(row["open"]) <= pos["stop"]:
                exit_px, reason = float(row["open"]), "stop_gap"
            elif float(row["low"]) <= pos["stop"]:
                exit_px, reason = pos["stop"], "stop"
            elif float(row["high"]) >= pos["target"]:
                exit_px, reason = pos["target"], "target"
            if exit_px is not None:
                fill = exit_px * (1 - cfg.slippage_rate)
                fees = pos["qty"] * (pos["entry"] + fill) * cfg.fee_rate
                pnl = pos["qty"] * (fill - pos["entry"]) - fees
                state["equity"] += pnl
                state["realized_pnl_today"] += pnl
                trade = {"event": "exit", "timestamp": iso, "entry_time": pos["time"],
                         "entry": pos["entry"], "exit": fill, "qty": pos["qty"],
                         "pnl_net": pnl, "reason": reason, "equity": state["equity"]}
                append_journal(trade, journal_path)
                events.append(trade)
                state["position"] = None
                if state["realized_pnl_today"] <= -state["equity"] * cfg.daily_loss_limit:
                    state["halted"] = True
                pos = None
        if pos is None and not state["halted"] and bool(prev["long_signal"]):
            atr = float(prev["atr"])
            if pd.notna(atr) and atr > 0:
                entry = float(row["open"]) * (1 + cfg.slippage_rate)
                stop = entry - cfg.stop_atr_multiple * atr
                target = entry + 2 * (entry - stop)
                if validate_long_trade(entry, stop, target):
                    costs = entry * (2 * cfg.fee_rate + 2 * cfg.slippage_rate)
                    qty = position_size(state["equity"], entry, stop, cfg.risk_per_trade, costs)
                    if qty > 0:
                        state["position"] = {"time": iso, "entry": entry, "stop": stop,
                                             "target": target, "qty": qty}
                        trade = {"event": "entry", "timestamp": iso, **state["position"],
                                 "equity": state["equity"], "mode": "PAPER_ONLY"}
                        append_journal(trade, journal_path)
                        events.append(trade)
        state["last_timestamp"] = iso
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, sort_keys=True, indent=2), encoding="utf-8")
    return {"mode": "PAPER_ONLY", "events_processed": len(events), "state": state,
            "warning": "Offline candle replay only; no exchange orders, no exact live fills, no liquidation model."}


def main():
    parser = argparse.ArgumentParser(description="Evaluate and journal a paper-only signal.")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--journal", default="data/paper_journal.jsonl")
    args = parser.parse_args()
    result = evaluate_latest(args.csv)
    append_journal(result, args.journal)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
