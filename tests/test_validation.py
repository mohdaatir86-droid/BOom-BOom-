import pandas as pd
import pytest
from bot.validation import chronological_split, walk_forward_windows


def candles(n=20):
    return pd.DataFrame({"timestamp":pd.date_range("2025-01-01",periods=n,freq="h",tz="UTC"),"close":range(n)})


def test_chronological_split_preserves_order_and_disjoint_windows():
    train, val, test = chronological_split(candles())
    assert len(train)==12 and len(val)==4 and len(test)==4
    assert train.timestamp.max() < val.timestamp.min()
    assert val.timestamp.max() < test.timestamp.min()


def test_walk_forward_windows_are_ordered_and_disjoint():
    df=candles(12)
    windows=list(walk_forward_windows(df,train_size=6,test_size=2))
    assert len(windows)==3
    for train,test in windows:
        assert train.timestamp.max() < test.timestamp.min()


def test_rejects_unordered_timestamps():
    df=candles()
    df.loc[4,"timestamp"]=df.loc[2,"timestamp"]
    with pytest.raises(ValueError,match="chronological"):
        chronological_split(df)
