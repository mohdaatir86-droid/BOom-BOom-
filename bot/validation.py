"""Time-ordered validation helpers. Never shuffle time-series observations."""
from __future__ import annotations
import pandas as pd


def chronological_split(df: pd.DataFrame, train_fraction=0.60, validation_fraction=0.20):
    if df.empty:
        raise ValueError("Dataframe cannot be empty")
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("Fractions must be between 0 and 1")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("Train plus validation fractions must be less than 1")
    if "timestamp" not in df.columns:
        raise ValueError("timestamp column is required")
    ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    if ts.isna().any() or not ts.is_monotonic_increasing or ts.duplicated().any():
        raise ValueError("Timestamps must be valid, unique and chronological")
    n=len(df)
    train_end=int(n*train_fraction)
    val_end=int(n*(train_fraction+validation_fraction))
    if train_end < 1 or val_end <= train_end or val_end >= n:
        raise ValueError("Not enough rows for the requested chronological split")
    return (df.iloc[:train_end].copy(), df.iloc[train_end:val_end].copy(), df.iloc[val_end:].copy())


def walk_forward_windows(df: pd.DataFrame, train_size: int, test_size: int, step_size: int | None=None):
    """Yield (train, test) windows with train strictly before test."""
    if "timestamp" not in df.columns:
        raise ValueError("timestamp column is required")
    ts=pd.to_datetime(df["timestamp"],utc=True,errors="coerce")
    if ts.isna().any() or not ts.is_monotonic_increasing or ts.duplicated().any():
        raise ValueError("Timestamps must be valid, unique and chronological")
    if train_size < 2 or test_size < 1:
        raise ValueError("train_size must be >=2 and test_size >=1")
    step = test_size if step_size is None else step_size
    if step < 1:
        raise ValueError("step_size must be >=1")
    start=train_size
    while start < len(df):
        end=min(start+test_size,len(df))
        yield df.iloc[start-train_size:start].copy(), df.iloc[start:end].copy()
        start += step
