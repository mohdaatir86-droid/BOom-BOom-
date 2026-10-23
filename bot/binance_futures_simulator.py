"""Data-driven Binance USDⓈ-M Futures risk simulator (offline, no order routing).

Load current exchangeInfo and authenticated leverageBracket responses externally.
Liquidation fees are configurable because they are not a single universal rate.
This is a research simulator, not an exact replica of Binance's risk engine:
it omits exchange-side liquidation execution, ADL, insurance fund behavior,
multi-assets portfolio margin, and intrabar mark-price paths.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import floor, isfinite
from typing import Any, Iterable, Mapping


def _number(name: str, value: Any, *, minimum: float = 0.0, strict: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not isfinite(result) or (result <= minimum if strict else result < minimum):
        op = "greater than" if strict else "at least"
        raise ValueError(f"{name} must be finite and {op} {minimum}")
    return result


@dataclass(frozen=True, order=True)
class MaintenanceBracket:
    """One Binance notional bracket; cum is Binance's cumulative maintenance amount."""
    notional_floor: float
    notional_cap: float
    maintenance_margin_rate: float
    cum: float = 0.0
    max_leverage: float | None = None

    def __post_init__(self) -> None:
        _number("notional_floor", self.notional_floor)
        _number("notional_cap", self.notional_cap, strict=True)
        _number("maintenance_margin_rate", self.maintenance_margin_rate)
        _number("cum", self.cum)
        if self.notional_cap <= self.notional_floor:
            raise ValueError("notional_cap must exceed notional_floor")
        if self.maintenance_margin_rate >= 1:
            raise ValueError("maintenance_margin_rate must be below 1")
        if self.max_leverage is not None:
            _number("max_leverage", self.max_leverage, strict=True)

    def maintenance_margin(self, notional: float) -> float:
        n = _number("notional", notional)
        if n < self.notional_floor or n > self.notional_cap:
            raise ValueError("notional is outside this maintenance bracket")
        return max(0.0, n * self.maintenance_margin_rate - self.cum)


@dataclass(frozen=True)
class BinanceMarketRules:
    """Relevant filters parsed from one USDⓈ-M exchangeInfo symbol record."""
    symbol: str
    status: str
    quantity_step: float
    min_quantity: float
    max_quantity: float
    market_quantity_step: float
    market_min_quantity: float
    market_max_quantity: float
    tick_size: float
    min_notional: float
    max_notional: float | None = None
    min_price: float = 0.0
    max_price: float | None = None
    percent_price_multiplier_up: float | None = None
    percent_price_multiplier_down: float | None = None
    max_num_orders: int | None = None
    max_num_algo_orders: int | None = None

    @classmethod
    def from_exchange_info(cls, symbol_record: Mapping[str, Any]) -> "BinanceMarketRules":
        filters = {f.get("filterType"): f for f in symbol_record.get("filters", [])}
        lot = filters.get("LOT_SIZE")
        market_lot = filters.get("MARKET_LOT_SIZE") or lot
        price = filters.get("PRICE_FILTER")
        notional = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL")
        if not lot or not market_lot or not price:
            raise ValueError("exchangeInfo record lacks LOT_SIZE, MARKET_LOT_SIZE, or PRICE_FILTER")
        min_notional = float((notional or {}).get("minNotional", 0) or 0)
        max_raw = (notional or {}).get("maxNotional")
        min_price = float(price.get("minPrice", 0) or 0)
        max_price_raw = price.get("maxPrice")
        percent = filters.get("PERCENT_PRICE")
        max_orders = filters.get("MAX_NUM_ORDERS")
        max_algo_orders = filters.get("MAX_NUM_ALGO_ORDERS")
        return cls(
            symbol=str(symbol_record["symbol"]),
            status=str(symbol_record.get("status", "UNKNOWN")),
            quantity_step=float(lot["stepSize"]),
            min_quantity=float(lot["minQty"]),
            max_quantity=float(lot["maxQty"]),
            market_quantity_step=float(market_lot["stepSize"]),
            market_min_quantity=float(market_lot["minQty"]),
            market_max_quantity=float(market_lot["maxQty"]),
            tick_size=float(price["tickSize"]),
            min_notional=min_notional,
            max_notional=float(max_raw) if max_raw not in (None, "") else None,
            min_price=min_price,
            max_price=float(max_price_raw) if max_price_raw not in (None, "") else None,
            percent_price_multiplier_up=float(percent["multiplierUp"]) if percent and percent.get("multiplierUp") else None,
            percent_price_multiplier_down=float(percent["multiplierDown"]) if percent and percent.get("multiplierDown") else None,
            max_num_orders=int(max_orders["limit"]) if max_orders and max_orders.get("limit") is not None else None,
            max_num_algo_orders=int(max_algo_orders["limit"]) if max_algo_orders and max_algo_orders.get("limit") is not None else None,
        )


    def validate_order_capacity(self, *, open_orders: int, open_algo_orders: int = 0) -> None:
        """Check known per-symbol order-count limits before a caller submits an order.

        Counts must include the proposed order where appropriate; this method only
        compares supplied counts with metadata limits and does not query an account.
        """
        if isinstance(open_orders, bool) or not isinstance(open_orders, int) or open_orders < 0:
            raise ValueError("open_orders must be a non-negative integer")
        if isinstance(open_algo_orders, bool) or not isinstance(open_algo_orders, int) or open_algo_orders < 0:
            raise ValueError("open_algo_orders must be a non-negative integer")
        if self.max_num_orders is not None and open_orders > self.max_num_orders:
            raise ValueError("MAX_NUM_ORDERS limit exceeded")
        if self.max_num_algo_orders is not None and open_algo_orders > self.max_num_algo_orders:
            raise ValueError("MAX_NUM_ALGO_ORDERS limit exceeded")

    @staticmethod
    def _round_down(value: float, step: float) -> float:
        return floor((value + step * 1e-10) / step) * step

    def validate_order(self, quantity: float, price: float, *, market: bool = False, reference_price: float | None = None) -> tuple[float, float]:
        if self.status != "TRADING":
            raise ValueError(f"{self.symbol} is not TRADING (status={self.status})")
        qty = _number("quantity", quantity, strict=True)
        px = _number("price", price, strict=True)
        step = self.market_quantity_step if market else self.quantity_step
        min_qty = self.market_min_quantity if market else self.min_quantity
        max_qty = self.market_max_quantity if market else self.max_quantity
        rounded_qty = self._round_down(qty, step)
        rounded_price = self._round_down(px, self.tick_size)
        if rounded_qty < min_qty:
            raise ValueError("quantity below minimum after step rounding")
        if rounded_qty > max_qty:
            raise ValueError("quantity exceeds maximum")
        if self.min_price and rounded_price < self.min_price:
            raise ValueError("price below PRICE_FILTER minimum")
        if self.max_price is not None and rounded_price > self.max_price:
            raise ValueError("price exceeds PRICE_FILTER maximum")
        if self.percent_price_multiplier_up is not None or self.percent_price_multiplier_down is not None:
            if reference_price is None:
                raise ValueError("reference_price is required to enforce PERCENT_PRICE filter")
            reference = _number("reference_price", reference_price, strict=True)
            if self.percent_price_multiplier_down is not None and rounded_price < reference * self.percent_price_multiplier_down:
                raise ValueError("price below PERCENT_PRICE lower band")
            if self.percent_price_multiplier_up is not None and rounded_price > reference * self.percent_price_multiplier_up:
                raise ValueError("price above PERCENT_PRICE upper band")
        notional = rounded_qty * rounded_price
        if self.min_notional and notional < self.min_notional:
            raise ValueError("notional below minimum")
        if self.max_notional is not None and notional > self.max_notional:
            raise ValueError("notional exceeds maximum")
        if rounded_price <= 0:
            raise ValueError("rounded price must be positive")
        return rounded_qty, rounded_price


def brackets_from_leverage_response(payload: Any, symbol: str | None = None) -> dict[str, tuple[MaintenanceBracket, ...]]:
    """Parse GET /fapi/v1/leverageBracket response, preserving per-symbol tiers."""
    records = payload if isinstance(payload, list) else [payload]
    output: dict[str, tuple[MaintenanceBracket, ...]] = {}
    for record in records:
        sym = str(record.get("symbol", ""))
        if symbol and sym != symbol:
            continue
        rows = record.get("brackets", [])
        tiers = []
        for row in rows:
            tiers.append(MaintenanceBracket(
                notional_floor=float(row["notionalFloor"]),
                notional_cap=float(row["notionalCap"]),
                maintenance_margin_rate=float(row["maintMarginRatio"]),
                cum=float(row.get("cum", 0)),
                max_leverage=float(row["initialLeverage"]) if row.get("initialLeverage") is not None else None,
            ))
        tiers.sort(key=lambda b: b.notional_floor)
        if not tiers:
            raise ValueError(f"no maintenance brackets returned for {sym or 'requested symbol'}")
        for previous, current in zip(tiers, tiers[1:]):
            if current.notional_floor > previous.notional_cap:
                raise ValueError(f"gap in maintenance brackets for {sym}")
        output[sym] = tuple(tiers)
    if symbol and symbol not in output:
        raise ValueError(f"no bracket data for {symbol}")
    return output


def bracket_for_notional(brackets: Iterable[MaintenanceBracket], notional: float) -> MaintenanceBracket:
    n = _number("notional", notional)
    tiers = tuple(sorted(brackets, key=lambda b: b.notional_floor))
    for tier in tiers:
        if tier.notional_floor <= n <= tier.notional_cap:
            return tier
    raise ValueError(f"notional {n} is outside supplied maintenance brackets")


@dataclass(frozen=True)
class CrossPosition:
    symbol: str
    side: str
    quantity: float
    entry_price: float
    brackets: tuple[MaintenanceBracket, ...]
    liquidation_fee_rate: float

    def __post_init__(self) -> None:
        if self.side not in ("LONG", "SHORT"):
            raise ValueError("side must be LONG or SHORT")
        _number("quantity", self.quantity, strict=True)
        _number("entry_price", self.entry_price, strict=True)
        if not self.brackets:
            raise ValueError("at least one maintenance bracket is required")
        _number("liquidation_fee_rate", self.liquidation_fee_rate)
        if self.liquidation_fee_rate >= 1:
            raise ValueError("liquidation_fee_rate must be below 1")

    @property
    def direction(self) -> int:
        return 1 if self.side == "LONG" else -1

    def pnl(self, mark_price: float) -> float:
        mark = _number("mark_price", mark_price, strict=True)
        return self.direction * self.quantity * (mark - self.entry_price)

    def notional(self, mark_price: float) -> float:
        return self.quantity * _number("mark_price", mark_price, strict=True)

    def maintenance_margin(self, mark_price: float) -> float:
        n = self.notional(mark_price)
        return bracket_for_notional(self.brackets, n).maintenance_margin(n)

    def liquidation_fee_reserve(self, mark_price: float) -> float:
        return self.notional(mark_price) * self.liquidation_fee_rate


@dataclass
class CrossMarginAccount:
    """Single-asset USDT cross-margin approximation with portfolio-level liquidation checks.

    wallet_balance is cash balance after realized PnL, trading fees and funding.
    marks must contain a positive mark price for every open position.
    """
    wallet_balance: float
    positions: list[CrossPosition]

    def __post_init__(self) -> None:
        _number("wallet_balance", self.wallet_balance)

    def equity(self, marks: Mapping[str, float]) -> float:
        return self.wallet_balance + sum(p.pnl(marks[p.symbol]) for p in self.positions)

    def maintenance_margin(self, marks: Mapping[str, float]) -> float:
        return sum(p.maintenance_margin(marks[p.symbol]) for p in self.positions)

    def liquidation_fee_reserve(self, marks: Mapping[str, float]) -> float:
        return sum(p.liquidation_fee_reserve(marks[p.symbol]) for p in self.positions)

    def margin_ratio(self, marks: Mapping[str, float]) -> float:
        mm = self.maintenance_margin(marks)
        if mm == 0:
            return 0.0
        return self.equity(marks) / mm

    def is_liquidation_triggered(self, marks: Mapping[str, float]) -> bool:
        return self.equity(marks) <= self.maintenance_margin(marks) + self.liquidation_fee_reserve(marks)

    def estimated_liquidation_price(self, symbol: str, marks: Mapping[str, float]) -> float:
        """Solve the portfolio trigger for one symbol, holding other marks constant.

        Returns a conservative numeric root estimate. Tier changes are handled by
        bisection on the monotonic trigger function; missing tier coverage raises.
        """
        target = next((p for p in self.positions if p.symbol == symbol), None)
        if target is None:
            raise ValueError(f"no open position for {symbol}")
        current = _number("mark price", marks[symbol], strict=True)
        other_marks = dict(marks)

        def breached(price: float) -> bool:
            candidate = dict(other_marks)
            candidate[symbol] = price
            return self.is_liquidation_triggered(candidate)

        # A position already beyond the trigger has no future adverse threshold to solve.
        if breached(current):
            raise ValueError("account is already at or beyond the liquidation trigger at current marks")
        # Search adverse direction and fail closed if the supplied tiers cannot bracket it.
        if target.side == "LONG":
            lo, hi = max(current * 1e-6, 1e-12), current
            if not breached(lo):
                raise ValueError("could not bracket long liquidation within supplied tiers")
            for _ in range(100):
                mid = (lo + hi) / 2
                if breached(mid):
                    lo = mid
                else:
                    hi = mid
            return (lo + hi) / 2
        else:
            lo = current
            # Stay inside the highest supplied bracket; never extrapolate a tier.
            hi = max(t.notional_cap for t in target.brackets) / target.quantity
            if hi <= lo or not breached(hi):
                raise ValueError("could not bracket short liquidation within supplied tiers")
            for _ in range(100):
                mid = (lo + hi) / 2
                if breached(mid):
                    hi = mid
                else:
                    lo = mid
            return (lo + hi) / 2
