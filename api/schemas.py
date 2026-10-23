"""Request/response models. Research/paper only — no live order fields."""
from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    status: str = "ok"
    mode: str = "research_paper_only"
    live_trading: bool = False
    version: str = "0.1.0"


class MarketInfo(BaseModel):
    symbol: str
    market_mode: str
    timeframes: list[str]
    notes: str


class MarketsResponse(BaseModel):
    markets: list[MarketInfo]
    live_orders: bool = False


class DataInspectRequest(BaseModel):
    csv_path: str = Field(..., description="Server-side relative path under data/ or absolute allowed research path")
    funding_csv: Optional[str] = None
    drop_incomplete_last: bool = True


class BacktestRequest(BaseModel):
    csv_path: str
    funding_csv: Optional[str] = None
    equity: float = Field(10_000.0, gt=0, le=10_000_000)
    fee_rate: float = Field(0.0006, ge=0, lt=0.05)
    slippage_rate: float = Field(0.0005, ge=0, lt=0.05)
    risk_per_trade: float = Field(0.0025, gt=0, le=0.05)
    target_r_multiple: float = Field(2.0, gt=0, le=20)
    drop_incomplete_last: bool = True

    @field_validator("csv_path")
    @classmethod
    def path_must_look_safe(cls, v: str) -> str:
        if ".." in v or v.startswith("~"):
            raise ValueError("Path must not contain .. or ~")
        return v


class WalkForwardRequest(BacktestRequest):
    train_size: int = Field(500, ge=50, le=5000)
    test_size: int = Field(100, ge=20, le=2000)


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    created_at: str
    updated_at: str
    job_type: str
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None
