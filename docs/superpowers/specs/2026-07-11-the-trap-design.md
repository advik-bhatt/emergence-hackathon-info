# The Trap — Design

**Date:** 2026-07-11
**Status:** Approved
**Builds on:** [`2026-07-11-promise-engine-design.md`](./2026-07-11-promise-engine-design.md)

A reframing of The Promise Engine around the trap hidden in Olist's data. Small build: one new
analysis module, one new agent tool, a live reasoning trace, and reframed copy. **The existing
product is not rebuilt.** No new CRAFT queries. No new tests (per user).

---

## 1. The thesis

The current product says: *set the promise to p95, hit 95% on-time.* Follow that logic honestly
and it does not stop there.

`fixtures/review_damage.json` — the measured damage curve:

| Bucket | Orders | Avg review | 1-star |
| --- | --- | --- | --- |
| Early | 88,163 | 4.29 | 6.6% |
| On time | 1,280 | 4.03 | 8.5% |
| 1–3 late | 1,852 | 3.29 | 25.2% |
| 4–7 late | 1,748 | 2.10 | 58.5% |
| 8–15 late | 1,601 | 1.68 | 70.0% |
| 15+ late | 1,188 | 1.75 | 68.9% |

**Early beats on-time.** Nothing in this dataset penalizes a *longer* promise.

So if reviews are the only measurable outcome — and in Olist they are, because there is no
clickstream — then **the review-maximizing delivery promise is unbounded.** Promise 60 days to
everyone. Every order lands early. Late rate → 0. Average review → 4.29. Every dashboard turns
green.

The cost of that — the customer who sees "delivery in 2 months" and leaves — is **structurally
unmeasurable in this data**, not merely unmeasured. Olist has no sessions, no page views, no cart
events.

**The data therefore contains a gradient that points off a cliff.** Any agent that optimizes the
measurable metric pads its way to a beautiful dashboard and a dead marketplace.

## 2. What this makes the product

The Promise Engine is no longer a delivery-date calculator. It is **the thing that refuses the
optimum.**

Its defining act: it can *prove* padding wins on the only metric it can see, and it **declines to
recommend it** — then falls back to a criterion that does not depend on the missing data.

That criterion is the median/variance decomposition already built:

- **Distance component** (`median`) — irreducible. The lane really is far. **PAD is honest.**
- **Variance component** (`p95 − median`) — recoverable. The lane is broken. **FIX it.**

> **Pará: median 21 days. It really is 2,500 km away. Padding is honest.**
> **Rio: median 12 days, next door to São Paulo. Padding is a lie you tell yourself. Fix it.**

The verdict rule stops being a heuristic someone picked. It becomes **the answer to the trap** —
the only honest arbiter available once you have refused to follow the gradient.

## 3. New: `analysis/trap.py`

Simulates the marketplace's review outcome as a function of a uniform promise extension.

```python
def review_curve(cassette) -> list[CurvePoint]
    """Expected avg review and 1-star rate if every promise were extended by D days,
    for D in 0..30."""

def naive_review_optimum(cassette) -> NaiveOptimum
    """The promise extension that maximizes measured reviews. It is unbounded."""
```

**Method.** Take the bucket counts from `review_damage`. Extending every promise by `D` days
migrates an order out of a lateness bucket if `D >= its days late`. Bucket midpoints are used for
the lateness of each bucket (1–3 → 2, 4–7 → 5.5, 8–15 → 11.5, 15+ → 20 as a conservative floor).
Migrated orders adopt the "Early" bucket's review score and 1-star rate. Recompute the
order-weighted average.

`NaiveOptimum` reports:
- `is_bounded: bool` → **False**
- `saturation_days: int` — the D beyond which the curve is flat (every order is early)
- `best_avg_review` / `best_one_star_rate` — the saturated values (4.29 / 6.6%)
- `verdict: str` — "UNBOUNDED — every additional day is free. The data never says stop."

**This is an approximation and says so.** Bucket midpoints, not exact per-order lateness. The
output states this in plain language; we do not hide it. The conclusion (monotone, never turns
over, unbounded) is robust to the approximation because *no bucket penalizes earliness* — the
result follows from the shape of the curve, not the precision of the midpoints.

## 4. New: the live reasoning trace

The demo must show the agent reasoning **live** — calling the optimizer, seeing "+∞", and turning
against it.

`Investigation` gains `steps: list[Step]`:

```python
@dataclass(frozen=True)
class Step:
    tool: str          # e.g. "naive_review_optimum"
    args: dict
    finding: str       # one line, what this call established
    kind: str          # "probe" | "trap" | "refusal" | "verdict"
```

`Tools` records every call it services. The loop assembles steps in order. Both paths — LLM and
scripted — produce a trace, so the demo is identical with or without `NEBIUS_API_KEY`.

The investigation's shape becomes:

1. **Probe** — falsify churn, bad-sellers. Both DEAD. (existing)
2. **Establish** — broken promises destroy reviews. SURVIVES. (existing)
3. **THE TRAP** — call `naive_review_optimum()`. It returns *unbounded: pad forever.*
4. **THE REFUSAL** — the agent declines. States why: the cost of a long promise is a customer who
   never orders; Olist has no clickstream; that cost is unmeasurable, so this metric cannot be
   optimized.
5. **THE RESOLUTION** — fall back to the structural criterion: distance vs. variance. Rank the
   lanes. Rio: FIX.

The LLM gets `naive_review_optimum` as a new tool, and a system prompt that instructs it to run the
naive optimization *before* recommending anything, and to reason explicitly about why it will not
follow it. The narrative guard applies unchanged — every number in the reasoning still has to come
from a tool.

## 5. Surfaces (small changes)

- **CLI** — a new "The Trap" section: the review curve as a sparkline/table climbing and
  flattening, the unbounded verdict, then the refusal. Then the existing work queue.
- **Web, Ops tab** — one new card above the work queue: the curve, the "+∞" result, the refusal.
  Steps render sequentially so it reads as reasoning, not as a table.
- **API** — `GET /investigation` also returns `steps` and `trap`.
- **README** — reframed around the trap.

## 6. What does not change

The verdict rule, lanes, quotes, seller attribution, seasonality, the narrative guard, the cassette,
the 112 existing tests. All intact.

## 7. Risks

| Risk | Mitigation |
| --- | --- |
| A judge attacks the midpoint approximation | We state it first, and the conclusion doesn't depend on it — no bucket penalizes earliness, so the curve cannot turn over |
| "You're claiming padding hurts conversion" — we are NOT | The claim is the opposite: the cost is *unmeasurable here*. Say it exactly that way. Never assert a conversion effect |
| Live LLM fails on stage | Scripted path produces the identical trace; the demo cannot fail open |
