import argparse
import pandas as pd
from .config import BotConfig
from .indicators import validate_ohlcv
from .strategy import generate_signals
from .risk import position_size, validate_long_trade

def run_backtest(df, config=None):
    cfg=config or BotConfig()
    validate_ohlcv(df)
    data=generate_signals(df,cfg).reset_index(drop=True)
    equity=peak=cfg.initial_equity
    max_dd=0.0
    position=None
    trades=[]
    for i in range(1,len(data)):
        row,prev=data.iloc[i],data.iloc[i-1]
        if position:
            exit_price,reason=None,""
            # Conservative assumption if stop and target hit in same candle: stop first.
            if row["low"] <= position["stop"]:
                exit_price,reason=position["stop"],"stop"
            elif row["high"] >= position["target"]:
                exit_price,reason=position["target"],"target"
            if exit_price is not None:
                fill=float(exit_price)*(1-cfg.slippage_rate)
                fees=position["qty"]*(position["entry"]+fill)*cfg.fee_rate
                pnl=position["qty"]*(fill-position["entry"])-fees
                equity+=pnl
                trades.append({"entry_time":position["time"],"exit_time":row["timestamp"],"entry":position["entry"],"exit":fill,"qty":position["qty"],"pnl_net":pnl,"reason":reason})
                position=None
                peak=max(peak,equity)
                max_dd=max(max_dd,(peak-equity)/peak if peak else 0)
        # Completed prior candle signal; next candle open entry.
        if position is None and bool(prev["long_signal"]):
            entry=float(row["open"])*(1+cfg.slippage_rate)
            atr=float(prev["atr"])
            if pd.isna(atr) or atr<=0: continue
            stop=entry-cfg.stop_atr_multiple*atr
            target=entry+2*(entry-stop)
            if not validate_long_trade(entry,stop,target): continue
            cost=entry*(2*cfg.fee_rate+2*cfg.slippage_rate)
            qty=position_size(equity,entry,stop,cfg.risk_per_trade,cost)
            if qty>0: position={"time":row["timestamp"],"entry":entry,"stop":stop,"target":target,"qty":qty}
    if position is not None and len(data):
        last=float(data.iloc[-1]["close"])*(1-cfg.slippage_rate)
        fees=position["qty"]*(position["entry"]+last)*cfg.fee_rate
        pnl=position["qty"]*(last-position["entry"])-fees
        equity+=pnl
        trades.append({"entry_time":position["time"],"exit_time":data.iloc[-1]["timestamp"],"entry":position["entry"],"exit":last,"qty":position["qty"],"pnl_net":pnl,"reason":"end_of_data"})
    wins=[t["pnl_net"] for t in trades if t["pnl_net"]>0]
    losses=[t["pnl_net"] for t in trades if t["pnl_net"]<=0]
    gp,gl=sum(wins),abs(sum(losses))
    return {"initial_equity":cfg.initial_equity,"final_equity":round(equity,2),"net_pnl":round(equity-cfg.initial_equity,2),"return_pct":round((equity/cfg.initial_equity-1)*100,3),"trades":len(trades),"win_rate_pct":round(len(wins)/len(trades)*100,2) if trades else 0.0,"profit_factor":round(gp/gl,3) if gl else None,"max_drawdown_pct":round(max_dd*100,3),"trades_detail":trades,"warning":"Simplified research backtest; not proof of live profitability."}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--csv",required=True)
    parser.add_argument("--equity",type=float,default=10000)
    args=parser.parse_args()
    result=run_backtest(pd.read_csv(args.csv),BotConfig(initial_equity=args.equity))
    for key,value in result.items():
        if key!="trades_detail": print(f"{key}: {value}")
    pd.DataFrame(result["trades_detail"]).to_csv("backtest_trades.csv",index=False)

if __name__=="__main__": main()
