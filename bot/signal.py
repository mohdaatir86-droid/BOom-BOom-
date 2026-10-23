import argparse
import pandas as pd
from .config import BotConfig
from .strategy import generate_signals

def main():
    parser=argparse.ArgumentParser(description="Paper-only signal output; no exchange orders")
    parser.add_argument("--csv",required=True)
    args=parser.parse_args()
    data=generate_signals(pd.read_csv(args.csv),BotConfig())
    last=data.iloc[-1]
    print("MODE: PAPER ONLY — no exchange orders are sent")
    for key in ("timestamp","close","ema_fast","ema_slow","rsi","long_signal"):
        print(f"{key}={last[key]}")

if __name__=="__main__": main()
