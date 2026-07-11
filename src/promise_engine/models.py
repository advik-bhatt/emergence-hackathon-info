from __future__ import annotations

import math
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

    def __post_init__(self) -> None:
        """Invariants that real data guarantees by construction. These cost nothing on the
        17 real lanes, but they convert a silent mis-resolved column (e.g. a re-record that
        renames a column so PROMISED_DAYS ends up holding the recommended promise instead of
        the current one) into a loud failure instead of a quietly wrong verdict."""
        if self.orders <= 0:
            raise ValueError(f"orders must be > 0, got {self.orders!r}")

        for field in ("promised_days", "median_days", "p95_days", "late_rate"):
            value = getattr(self, field)
            if not math.isfinite(value):
                raise ValueError(f"{field} must be finite, got {value!r}")

        if not self.promised_days > 0:
            raise ValueError(f"promised_days must be > 0, got {self.promised_days!r}")

        if not 0.0 <= self.median_days <= self.p95_days:
            raise ValueError(
                f"expected 0 <= median_days <= p95_days, got median_days="
                f"{self.median_days!r}, p95_days={self.p95_days!r} (a p95 cannot fall "
                f"below its own median)"
            )

        if not 0.0 <= self.late_rate <= 1.0:
            raise ValueError(f"late_rate must be in [0.0, 1.0], got {self.late_rate!r}")

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
