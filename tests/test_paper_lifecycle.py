import json
import pandas as pd
import pytest
import bot.paper as paper

def candles():
    return pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=5, freq="h", tz="UTC"),
        "open": [100.] * 5, "high": [101.] * 5, "low": [99., 99., 97., 99., 99.],
        "close": [100., 100., 99., 100., 100.], "volume": [1.] * 5,
    })

def test_paper_simulation_persists_and_replay_is_idempotent(tmp_path, monkeypatch):
    data = candles()
    signals = data.copy()
    signals["atr"] = [1.] * len(data)
    signals["long_signal"] = [False, True, False, False, False]
    monkeypatch.setattr(paper, "generate_signals", lambda df, cfg: signals.copy())
    state, journal = tmp_path / "state.json", tmp_path / "trades.jsonl"
    paper.run_paper_simulation(data, state_path=str(state), journal_path=str(journal))
    first = journal.read_text().splitlines()
    paper.run_paper_simulation(data, state_path=str(state), journal_path=str(journal))
    assert journal.read_text().splitlines() == first
    assert json.loads(state.read_text())["last_timestamp"] is not None

def test_corrupted_state_has_clear_error(tmp_path):
    state = tmp_path / "state.json"
    state.write_text("{broken")
    with pytest.raises(ValueError, match="Corrupted paper state"):
        paper.run_paper_simulation(candles(), state_path=str(state), journal_path=str(tmp_path / "journal.jsonl"))

def test_duplicate_timestamps_rejected(tmp_path):
    data = candles()
    data.loc[2, "timestamp"] = data.loc[1, "timestamp"]
    with pytest.raises(ValueError):
        paper.run_paper_simulation(data, state_path=str(tmp_path / "state.json"), journal_path=str(tmp_path / "journal.jsonl"))
