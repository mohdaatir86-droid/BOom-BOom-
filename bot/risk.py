
from dataclasses import dataclass
from math import floor


@dataclass
class RiskState:
    start_of_day_equity: float
    realized_pnl_today: float = 0.0
    halted: bool = False
    halt_reason: str = ""

    def record_realized_pnl(self, pnl: float, daily_loss_limit: float) -> None:
        self.realized_pnl_today += pnl
        self.check_daily_loss(0.0, daily_loss_limit)

    def check_daily_loss(self, unrealized_pnl: float, daily_loss_limit: float) -> None:
        """Halt new entries on combined realized + unrealized daily loss."""
        if daily_loss_limit <= 0:
            return
        if self.realized_pnl_today + float(unrealized_pnl) <= -(self.start_of_day_equity * daily_loss_limit):
            self.halted = True
            self.halt_reason = "daily_loss_limit"

    def can_open_new_position(self) -> bool:
        return not self.halted


def position_size(equity, entry, stop, risk_fraction, estimated_cost_per_unit=0.0, quantity_step=0.000001):
    """Linear sizing helper; venue lot, notional, exposure and liquidation rules remain external."""
    if equity <= 0 or entry <= 0 or stop <= 0 or risk_fraction <= 0 or quantity_step <= 0:
        return 0.0
    risk_per_unit = abs(entry - stop) + max(estimated_cost_per_unit, 0.0)
    if risk_per_unit <= 0:
        return 0.0
    return floor((equity * risk_fraction / risk_per_unit) / quantity_step) * quantity_step


def validate_long_trade(entry, stop, target):
    return entry > 0 and stop > 0 and target > 0 and stop < entry < target
