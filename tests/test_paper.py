import pandas as pd
import pytest

import bot.paper as paper


def test_paper_signal_uses_last_completed_candle(tmp_path, monkeypatch):
    csv_path = tmp_path / "candles.csv"
    pd.DataFrame({"timestamp": ["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z", "2026-01-01T02:00:00Z"],
                  "open": [10, 11, 12], "high": [11, 12, 13], "low": [9, 10, 11],
                  "close": [10, 11, 12], "volume": [1, 1, 1]}).to_csv(csv_path, index=False)
    signals = pd.read_csv(csv_path)
    signals["ema_fast"] = [None, 10.5, 11.5]
    signals["ema_slow"] = [None, 10.0, 11.0]
    signals["rsi"] = [None, 55.0, 60.0]
    signals["atr"] = [None, 1.0, 1.0]
    signals["long_signal"] = [False, True, True]
    monkeypatch.setattr(paper, "generate_signals", lambda data, cfg: signals)
    result = paper.evaluate_latest(str(csv_path))
    assert result["timestamp"] == "2026-01-01T01:00:00Z"
    assert result["long_signal"] is True


def test_paper_signal_requires_two_candles(tmp_path):
    csv_path = tmp_path / "one.csv"
    pd.DataFrame({"timestamp": ["2026-01-01T00:00:00Z"], "open": [10], "high": [11],
                  "low": [9], "close": [10], "volume": [1]}).to_csv(csv_path, index=False)
    with pytest.raises(ValueError, match="two candles"):
        paper.evaluate_latest(str(csv_path))
