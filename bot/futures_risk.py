"""Conservative, exchange-agnostic linear USDT-margined futures risk estimates.

These formulas are screening estimates only. They do not model Binance's
maintenance-margin brackets, wallet/cross margin, fee tiers, funding accrued
after entry, liquidation fees, mark-price path, ADL, or exchange-specific rules.
Never use them as an exchange liquidation guarantee or for live order routing.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import floor, isfinite


def _positive(name: str, value: float) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be finite and positive")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite and positive") from exc
    if not isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return number


@dataclass(frozen=True)
class LinearFuturesPosition:
    entry_price: float
    quantity: float
    leverage: float
    maintenance_margin_rate: float = 0.005
    entry_fee_rate: float = 0.0005
    isolated_wallet_margin: float | None = None

    def __post_init__(self) -> None:
        for name in ("entry_price", "quantity", "leverage"):
            _positive(name, getattr(self, name))
        for name in ("maintenance_margin_rate", "entry_fee_rate"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isfinite(float(value)) or not 0 <= value < 1:
                raise ValueError(f"{name} must be finite and in [0, 1)")
        if self.leverage < 1:
            raise ValueError("leverage must be at least 1")
        if self.maintenance_margin_rate >= 1 / self.leverage:
            raise ValueError("maintenance margin rate must be below initial margin rate")
        if self.isolated_wallet_margin is not None:
            _positive("isolated_wallet_margin", self.isolated_wallet_margin)

    @property
    def notional(self) -> float:
        return self.entry_price * self.quantity

    @property
    def estimated_initial_margin(self) -> float:
        return self.notional / self.leverage

    @property
    def estimated_entry_fee(self) -> float:
        return self.notional * self.entry_fee_rate

    def unrealized_pnl(self, mark_price: float, side: str = "long") -> float:
        mark = _positive("mark_price", mark_price)
        direction = _direction(side)
        return direction * self.quantity * (mark - self.entry_price)

    def estimated_liquidation_price(self, side: str = "long") -> float:
        """Estimate liquidation mark for isolated linear margin, excluding extra margin.

        Approximation: long = entry * (1 - 1/leverage + MMR);
        short = entry * (1 + 1/leverage - MMR). Entry fee is not included
        in this simplified formula; actual venue liquidation differs.
        """
        direction = _direction(side)
        if self.isolated_wallet_margin is None:
            margin_fraction = 1.0 / self.leverage
        else:
            margin_fraction = self.isolated_wallet_margin / self.notional
        if direction == 1:
            price = self.entry_price * (1 - margin_fraction + self.maintenance_margin_rate)
        else:
            price = self.entry_price * (1 + margin_fraction - self.maintenance_margin_rate)
        if price <= 0:
            raise ValueError("estimated liquidation price is non-positive; position assumptions are invalid")
        return price

    def margin_remaining(self, mark_price: float, side: str = "long") -> float:
        """Approximate isolated margin remaining after unrealized PnL and entry fee."""
        wallet = self.isolated_wallet_margin
        if wallet is None:
            wallet = self.estimated_initial_margin
        return wallet + self.unrealized_pnl(mark_price, side) - self.estimated_entry_fee


def _direction(side: str) -> int:
    if side == "long":
        return 1
    if side == "short":
        return -1
    raise ValueError("side must be 'long' or 'short'")


@dataclass(frozen=True)
class LinearMarketRules:
    """A small set of venue filters; populate from current exchange metadata."""
    quantity_step: float
    min_quantity: float
    tick_size: float
    min_notional: float = 0.0

    def __post_init__(self) -> None:
        for name in ("quantity_step", "min_quantity", "tick_size"):
            _positive(name, getattr(self, name))
        if isinstance(self.min_notional, bool) or not isfinite(float(self.min_notional)) or self.min_notional < 0:
            raise ValueError("min_notional must be finite and non-negative")

    def round_quantity_down(self, quantity: float, price: float) -> float:
        qty = _positive("quantity", quantity)
        px = _positive("price", price)
        rounded = floor((qty + self.quantity_step * 1e-10) / self.quantity_step) * self.quantity_step
        if rounded < self.min_quantity:
            raise ValueError("quantity is below the market minimum after step rounding")
        if rounded * px < self.min_notional:
            raise ValueError("notional is below the market minimum")
        return rounded

    def round_price(self, price: float, *, upward: bool = False) -> float:
        px = _positive("price", price)
        units = px / self.tick_size
        rounded_units = floor(units + 1e-10) if not upward else -floor(-units + 1e-10)
        rounded = rounded_units * self.tick_size
        if rounded <= 0:
            raise ValueError("rounded price must remain positive")
        return rounded
