"""Read-only Binance USD-M open-interest history adapter via public endpoints."""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd


def normalize_open_interest(rows) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["timestamp", "sum_open_interest", "sum_open_interest_value"])
    out=[]
    for row in rows:
        ts=row.get("timestamp")
        oi=row.get("sumOpenInterest")
        value=row.get("sumOpenInterestValue")
        if ts is None or oi is None:
            continue
        timestamp=pd.to_datetime(ts,unit="ms",utc=True,errors="coerce")
        try:
            oi=float(oi)
            value=float(value) if value is not None else float("nan")
        except (TypeError,ValueError):
            continue
        if pd.isna(timestamp) or pd.isna(oi) or oi < 0:
            continue
        out.append({"timestamp":timestamp,"sum_open_interest":oi,"sum_open_interest_value":value})
    df=pd.DataFrame(out,columns=["timestamp","sum_open_interest","sum_open_interest_value"])
    if df.empty:
        return df
    return df.drop_duplicates("timestamp",keep="last").sort_values("timestamp").reset_index(drop=True)


def download_open_interest_history(symbol="BTCUSDT", period="1h", limit=500):
    """Fetch Binance futures /futures/data/openInterestHist public endpoint."""
    if not isinstance(limit,int) or not 1 <= limit <= 500:
        raise ValueError("limit must be an integer between 1 and 500")
    if period not in {"5m","15m","30m","1h","2h","4h","6h","12h","1d"}:
        raise ValueError("Unsupported Binance open-interest period")
    import requests
    response=requests.get(
        "https://fapi.binance.com/futures/data/openInterestHist",
        params={"symbol":symbol.replace("/","").replace(":USDT",""),"period":period,"limit":limit},
        timeout=15,
    )
    response.raise_for_status()
    payload=response.json()
    if isinstance(payload,dict) and "code" in payload:
        raise RuntimeError(f"Binance API error: {payload.get('code')} {payload.get('msg')}")
    return normalize_open_interest(payload)


def main():
    parser=argparse.ArgumentParser(description="Fetch public Binance Futures open-interest history.")
    parser.add_argument("--symbol",default="BTCUSDT")
    parser.add_argument("--period",default="1h")
    parser.add_argument("--limit",type=int,default=500)
    parser.add_argument("--out",default="data/BTC_USDT_open_interest.csv")
    args=parser.parse_args()
    data=download_open_interest_history(args.symbol,args.period,args.limit)
    output=Path(args.out); output.parent.mkdir(parents=True,exist_ok=True)
    data.to_csv(output,index=False)
    print(f"Saved {len(data)} open-interest records to {output}")
    if data.empty: print("WARNING: no open-interest records returned.")
    print("Public endpoint only; no API keys or orders used.")


if __name__=="__main__": main()
