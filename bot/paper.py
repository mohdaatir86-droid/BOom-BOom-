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
