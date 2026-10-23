import pandas as pd
from bot.open_interest import normalize_open_interest


def test_normalize_open_interest_sorts_and_deduplicates():
    rows=[
      {"timestamp":1735718400000,"sumOpenInterest":"12.0","sumOpenInterestValue":"1200"},
      {"timestamp":1735689600000,"sumOpenInterest":"10.0","sumOpenInterestValue":"1000"},
      {"timestamp":1735718400000,"sumOpenInterest":"13.0","sumOpenInterestValue":"1300"},
    ]
    result=normalize_open_interest(rows)
    assert len(result)==2
    assert result.timestamp.is_monotonic_increasing
    assert result.iloc[-1].sum_open_interest==13.0
    assert str(result.timestamp.dt.tz)=="UTC"


def test_empty_open_interest_is_schema_stable():
    result=normalize_open_interest([])
    assert result.empty
    assert list(result.columns)==["timestamp","sum_open_interest","sum_open_interest_value"]
