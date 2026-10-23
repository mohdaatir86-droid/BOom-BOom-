"""Read-only web API for BOom-Boom research tools. No order endpoints exist."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from bot.backtest import run_backtest
from bot.config import BotConfig
from bot.data import download_ohlcv
from bot.walk_forward import evaluate_walk_forward

app = FastAPI(
    title="BOom-Boom Research API",
    version="0.1.0",
    description="Historical research and paper-only diagnostics. No live order endpoints.",
)

class ResearchRequest(BaseModel):
    symbol: Literal["BTC/USDT", "ETH/USDT"] = "BTC/USDT"
    timeframe: Literal["15m", "1h", "4h", "1d"] = "1h"
    candles: int = Field(default=500, ge=100, le=1000)
    initial_equity: float = Field(default=10000, gt=0, le=100000000)
    fee_rate: float = Field(default=0.0006, ge=0, lt=0.1)
    slippage_rate: float = Field(default=0.0005, ge=0, lt=0.1)
    train_size: int = Field(default=300, ge=50, le=800)
    test_size: int = Field(default=100, ge=20, le=500)

def config_for(req: ResearchRequest) -> BotConfig:
    return BotConfig(
        initial_equity=req.initial_equity,
        fee_rate=req.fee_rate,
        slippage_rate=req.slippage_rate,
    )

def load_candles(req: ResearchRequest) -> pd.DataFrame:
    try:
        candles = download_ohlcv(
            exchange_id="binance",
            symbol=req.symbol,
            timeframe=req.timeframe,
            limit=req.candles,
        )
        # The newest public candle can still be in progress. Exclude it from
        # research so the UI does not silently score an incomplete candle.
        if len(candles) > 2:
            candles = candles.iloc[:-1].reset_index(drop=True)
        return candles
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Public market-data request failed: {exc}") from exc

def clean_trade(trade: dict) -> dict:
    cleaned = {}
    for key, value in trade.items():
        if hasattr(value, "isoformat"):
            cleaned[key] = value.isoformat()
        elif hasattr(value, "item"):
            cleaned[key] = value.item()
        else:
            cleaned[key] = value
    return cleaned

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "BOom-Boom Research API",
        "mode": "historical_research_only",
        "live_orders_enabled": False,
        "data_source": "Binance public OHLCV via CCXT",
    }

@app.post("/api/backtest")
async def backtest(req: ResearchRequest):
    candles = await run_in_threadpool(load_candles, req)
    try:
        result = await run_in_threadpool(run_backtest, candles, config_for(req))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Backtest rejected the data/configuration: {exc}") from exc
    result.pop("trades_detail", None)
    result.update({
        "symbol": req.symbol,
        "timeframe": req.timeframe,
        "candles_used": len(candles),
        "data_start": pd.to_datetime(candles["timestamp"].iloc[0], utc=True).isoformat(),
        "data_end": pd.to_datetime(candles["timestamp"].iloc[-1], utc=True).isoformat(),
        "data_source": "Binance public OHLCV",
        "latest_candle_excluded": True,
        "mode": "historical_research_only",
        "live_orders_enabled": False,
    })
    return result

@app.post("/api/walk-forward")
async def walk_forward(req: ResearchRequest):
    if req.train_size + req.test_size > req.candles:
        raise HTTPException(status_code=422, detail="Train size + test size must not exceed requested candle count.")
    candles = await run_in_threadpool(load_candles, req)
    if req.train_size + req.test_size > len(candles):
        raise HTTPException(status_code=422, detail="Not enough completed candles for the chosen train/test sizes.")
    try:
        result = await run_in_threadpool(
            evaluate_walk_forward,
            candles,
            config_for(req),
            req.train_size,
            req.test_size,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Walk-forward evaluation failed: {exc}") from exc
    result.update({
        "symbol": req.symbol,
        "timeframe": req.timeframe,
        "candles_used": len(candles),
        "data_start": pd.to_datetime(candles["timestamp"].iloc[0], utc=True).isoformat(),
        "data_end": pd.to_datetime(candles["timestamp"].iloc[-1], utc=True).isoformat(),
        "data_source": "Binance public OHLCV",
        "latest_candle_excluded": True,
        "live_orders_enabled": False,
    })
    return result

@app.get("/")
def portal():
    return FileResponse("web/index.html")

app.mount("/assets", StaticFiles(directory="web"), name="assets")
