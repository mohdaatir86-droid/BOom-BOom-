import pandas as pd
from bot.candles import add_candlestick_patterns

def test_doji_and_hammer_are_detected():
    df = pd.DataFrame({"open":[10.0,10.0],"high":[10.2,10.2],"low":[9.8,8.0],"close":[10.01,10.1]})
    result = add_candlestick_patterns(df)
    assert bool(result.loc[0,"candle_doji"])
    assert bool(result.loc[1,"candle_hammer"])

def test_bullish_engulfing_detected():
    df = pd.DataFrame({"open":[10.0,8.8],"high":[10.1,10.2],"low":[8.5,8.7],"close":[9.0,10.0]})
    result = add_candlestick_patterns(df)
    assert bool(result.loc[1,"candle_bullish_engulfing"])

def test_pattern_columns_are_boolean_values():
    df = pd.DataFrame({"open":[10.0,9.0,9.5],"high":[10.5,10.0,10.5],"low":[9.5,8.5,9.0],"close":[10.0,9.8,10.2]})
    result = add_candlestick_patterns(df)
    cols = [c for c in result.columns if c.startswith("candle_")]
    assert result[cols].notna().all().all()
    assert not bool(result.loc[0,"candle_bullish_engulfing"])
