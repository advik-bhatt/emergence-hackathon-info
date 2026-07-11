from __future__ import annotations

from dataclasses import dataclass

from promise_engine.analysis.verdict import Verdict, decide, variance_share


@dataclass(frozen=True)
class Lane:
    """One destination state: what we promise, and what we'd need to promise."""

    state: str
    orders: int
    promised_days: float
    median_days: float
    p95_days: float
    late_rate: float

    @property
    def recommended_promise(self) -> float:
        """The promise that actually hits 95% on-time."""
        return self.p95_days

    @property
    def gap(self) -> float:
        """Days we are short. Positive means we are over-promising."""
        return self.recommended_promise - self.promised_days

    @property
    def orders_at_risk(self) -> float:
        """The ops queue's sort key: how much broken promise this lane ships.

        A lane we have judged OK carries no risk by definition, even though its gap may be
        fractionally positive. Without this, SP (gap +0.2 x 40,501 orders) would score 8,100
        and outrank Para — sending ops to fix a lane that is already calibrated.
        """
        if self.verdict is Verdict.OK:
            return 0.0
        return max(self.gap, 0.0) * self.orders

    @property
    def variance_share(self) -> float:
        return variance_share(self.median_days, self.p95_days)

    @property
    def tail_days(self) -> float:
        """The recoverable part of the promise: tail, not distance."""
        return self.p95_days - self.median_days

    @property
    def verdict(self) -> Verdict:
        return decide(
            promised_days=self.promised_days,
            median_days=self.median_days,
            p95_days=self.p95_days,
        )
