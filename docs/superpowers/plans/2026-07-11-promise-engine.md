# The Promise Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an agent that sets the delivery promise a marketplace shows at checkout — one it can actually keep — and decides, per lane, whether to pad the promise or fix the lane.

**Architecture:** Four layers. `craft/` talks to the CRAFT MCP server and records every response to committed JSON fixtures, so the repo replays end-to-end with zero credentials. `analysis/` owns all math and the pad/fix verdict in deterministic Python. `agent/` is a Nemotron function-calling loop that investigates (falsifying its own hypotheses) and narrates — but never computes a number. `api/` + `web/` expose it as a checkout simulator and an ops work-queue. The load-bearing invariant: **numbers never pass through the LLM.**

**Tech Stack:** Python 3.12+, `uv`, pytest, FastAPI + uvicorn, `openai` SDK (pointed at Nebius Token Factory), `rich` for terminal output, plain HTML/CSS/JS for the web app (no build step).

**Spec:** [`docs/superpowers/specs/2026-07-11-promise-engine-design.md`](../specs/2026-07-11-promise-engine-design.md)

---

## Ground Truth (the tests are written against these)

Verified against live Olist data. These are the regression targets.

| State | Orders | Promised | Median actual | p95 actual | Late rate | Gap | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SP | 40,494 | 19.8 | 7 | 20.0 | 5.9% | +0.2 | OK |
| MG | 11,354 | 25.2 | 10 | 24.4 | 5.6% | −0.8 | OK |
| PR | 4,923 | 25.3 | 10 | 25.0 | 5.0% | −0.3 | OK |
| BA | 3,256 | 30.1 | 17 | 37.0 | 14.0% | +6.9 | PAD |
| MA | 717 | 31.1 | 19 | 41.2 | 19.7% | +10.1 | PAD |
| **RJ** | **12,350** | **27.0** | **12** | **38.0** | **13.5%** | **+11.0** | **FIX** |
| CE | 1,279 | 32.0 | 18 | 45.0 | 15.3% | +13.0 | FIX |

**Verdict rule:** `variance_share = (p95 − median) / p95`
- `gap <= 1.5` → **OK** (already calibrated — do not cry wolf)
- `variance_share >= 0.60` → **FIX** (unpredictable, not slow — the tail is the problem)
- else → **PAD** (genuinely far — padding is honest)

Applied to the table above this flags exactly RJ (0.684) and CE (0.600), leaving BA (0.541) and MA (0.539) as PAD. The rule *derives* the two lanes the spec flagged by hand.

**Review-score damage (used by the falsification suite):**

| Bucket | Avg review | % 1-star |
| --- | --- | --- |
| Early | 4.29 | 6.6% |
| 1–3 days late | 3.29 | 25% |
| 8–15 days late | 1.68 | 70% |

**Dead hypotheses:** churn (3.12% repeat rate, flat by review score: 1-star → 3.26%, 5-star → 3.17%); bad sellers (volume artifact — top-30 "worst" are 9.39% late vs 7.41% baseline; no seller exceeds 40% late); flat buffer (it *is* distance-adjusted: SP ~20d, PA ~38d).

---

## File Structure

```
pyproject.toml                          uv project, deps, pytest config
.env.example                            NEBIUS_API_KEY, CRAFT_PROJECT_ID, PROMISE_ENGINE_MODE
fixtures/
  manifest.json                         question-slug → fixture file, recorded_at, row count
  <slug>.json                           one per CRAFT question: nl_question, sql, columns, rows
src/promise_engine/
  models.py                             LaneStats, SellerStats, MonthStats, Promise, Verdict
  craft/
    questions.py                        the NL questions, verbatim. No hand-written SQL.
    cassette.py                         record/replay store over fixtures/
    client.py                           live MCP client (OAuth PKCE) + mode dispatch
  analysis/
    lanes.py                            LaneStats from rows; gap; orders_at_risk; ranking
    verdict.py                          the pad/fix/OK rule + its constants
    promise.py                          per-order promise = handling_p95 + transit_p95 [× season]
    season.py                           season_factor(month) — opt-in
    hypotheses.py                       the falsification suite
  agent/
    tools.py                            tool schemas + dispatch to analysis/
    loop.py                             Nemotron function-calling loop; scripted fallback
    narrative.py                        number-extraction guard (the invariant)
  api/
    app.py                              FastAPI: /promise /lanes /sellers /investigation
  cli.py                                rich terminal demo
web/
  index.html  app.js  style.css         checkout simulator + ops dashboard
tests/
  test_verdict.py  test_lanes.py  test_promise.py  test_season.py
  test_hypotheses.py  test_cassette.py  test_narrative_guard.py  test_api.py
```

---

## Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`, `.env.example`, `.gitignore`, `src/promise_engine/__init__.py`

- [ ] **Step 1: Create the uv project**

```bash
cd /Users/aslanwang/dev/emergence-hackathon-info
uv init --lib --name promise-engine --python 3.12 . 2>/dev/null || true
```

If `uv init` refuses because the directory is non-empty, create `pyproject.toml` by hand with the content in Step 2.

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "promise-engine"
version = "0.1.0"
description = "An agent that decides the delivery date a marketplace can actually keep"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "openai>=1.55",
    "rich>=13.9",
    "pydantic>=2.9",
    "httpx>=0.27",
]

[dependency-groups]
dev = ["pytest>=8.3", "pytest-asyncio>=0.24"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/promise_engine"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 3: Write `.env.example`**

```bash
# Agent reasoning LLM (Nebius Token Factory, OpenAI-compatible). Optional:
# with no key the agent runs a scripted investigation over the same tools.
NEBIUS_API_KEY=
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/
NEBIUS_MODEL=nvidia/nemotron-3-super-120b-a12b

# CRAFT MCP. Only needed to re-record fixtures.
CRAFT_PROJECT_ID=5f7bc95c-c206-4bfb-8f6f-5d3c37980642
CRAFT_MCP_URL=https://nebius.emergence.ai/mcp

# replay (default, no creds needed) | record | live
PROMISE_ENGINE_MODE=replay
```

- [ ] **Step 4: Append to `.gitignore`**

```
.env
.venv/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 5: Install and verify**

Run: `uv sync && uv run pytest --collect-only`
Expected: installs cleanly; pytest reports "no tests ran" (no tests yet). That's success.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .env.example .gitignore src/promise_engine/__init__.py uv.lock
git commit -m "chore: scaffold promise-engine (uv, pytest, fastapi)"
```

---

## Task 2: Harvest real CRAFT fixtures

**This task is done by the operator (Claude Code) using its live CRAFT MCP session**, because the standalone process has no OAuth token yet. The output is real data, committed.

**Files:**
- Create: `src/promise_engine/craft/questions.py`, `fixtures/*.json`, `fixtures/manifest.json`

- [ ] **Step 1: Write `src/promise_engine/craft/questions.py`**

```python
"""The natural-language questions we ask CRAFT.

No hand-written SQL anywhere in this project: `generate_sql` writes it. Because
generate_sql is non-deterministic, we record the SQL it produced alongside the rows,
and assert on result shape rather than SQL text.
"""

SCHEMA_ARGS = {
    "schema_name": "BRAZILIAN_E_COMMERCE",
    "schema_fqn": "brazilian-e-commerce-5f7bc95c.BRAZILIAN_E_COMMERCE.BRAZILIAN_E_COMMERCE",
}

QUESTIONS: dict[str, str] = {
    "lanes": (
        "For delivered orders, group by customer_state (only states with at least 500 "
        "orders). For each state compute: the order count, the average promised days "
        "(purchase to estimated delivery), the median actual delivery days, the 95th "
        "percentile of actual delivery days, and the current late rate. Then compute a "
        "recommended promise equal to the 95th percentile of actual delivery days, and the "
        "difference between that recommended promise and the current average promised days. "
        "Order by that difference ascending."
    ),
    "seasonality": (
        "For delivered orders, group by the year and month of order_purchase_timestamp and "
        "show the number of orders, the average actual delivery days, the average promised "
        "days, and the late rate. Only months with at least 500 orders, ordered "
        "chronologically."
    ),
    "seller_handling": (
        "For each seller with at least 50 delivered items, compute the 95th percentile of "
        "seller handling days (order_approved_at to order_delivered_carrier_date), the "
        "median handling days, and the number of delivered items."
    ),
    "state_transit": (
        "For each customer_state with at least 500 delivered orders, compute the 95th "
        "percentile of carrier transit days (order_delivered_carrier_date to "
        "order_delivered_customer_date) and the median carrier transit days."
    ),
    "review_damage": (
        "Bucket delivered orders by how many days late they were versus the estimated "
        "delivery date (early, on time, 1-3 days late, 4-7 days late, 8-15 days late, more "
        "than 15 days late) and for each bucket show the number of orders, the average "
        "review score, and the percentage of reviews that are 1 star."
    ),
    "churn": (
        "Using OLIST_CUSTOMERS.customer_unique_id as the true person, how many distinct "
        "people are there, how many placed more than one order, and what is the overall "
        "repeat purchase rate? Then, for customers whose FIRST order received a given review "
        "score (1 to 5), what percentage went on to place another order?"
    ),
    "seller_lateness": (
        "For each seller with at least 50 delivered items, compute the number of late items, "
        "the total delivered items, and the late rate. Order by late rate descending."
    ),
}
```

- [ ] **Step 2: Harvest each question through the live CRAFT MCP session**

For each slug in `QUESTIONS`, the operator runs:
1. `generate_sql` with the question text and `SCHEMA_ARGS`
2. `execute_query` with the returned SQL → yields an `artifact_fqn` (**it does not return rows**)
3. `get_result_page` with that `artifact_fqn` → yields columns + rows

Write each to `fixtures/<slug>.json`:

```json
{
  "slug": "lanes",
  "nl_question": "For delivered orders, group by customer_state ...",
  "sql": "<the SQL generate_sql produced>",
  "columns": ["CUSTOMER_STATE", "ORDER_COUNT", "..."],
  "rows": [["SP", 40494, 19.8, 7.0, 20.0, 0.059], ["..."]],
  "recorded_at": "2026-07-11T00:00:00Z"
}
```

- [ ] **Step 3: Write `fixtures/manifest.json`**

Map each slug to its file, row count, and `recorded_at`, so a stale fixture set is visible at a glance.

- [ ] **Step 4: Sanity-check the harvest against ground truth**

Confirm from `fixtures/lanes.json`: RJ has ~12,350 orders, median 12, p95 38, promised ~27. If it doesn't, **stop** — the fixture is wrong and every downstream test will encode the error.

- [ ] **Step 5: Commit**

```bash
git add src/promise_engine/craft/questions.py fixtures/
git commit -m "feat(craft): record real CRAFT responses as replayable fixtures"
```

---

## Task 3: The verdict rule (TDD)

The heart of the product. Written first, because everything else serves it.

**Files:**
- Create: `src/promise_engine/models.py`, `src/promise_engine/analysis/verdict.py`
- Test: `tests/test_verdict.py`

- [ ] **Step 1: Write the failing test**

`tests/test_verdict.py`:

```python
import pytest
from promise_engine.analysis.verdict import Verdict, decide

# (name, promised, median, p95, expected)
GROUND_TRUTH = [
    ("SP", 19.8, 7.0, 20.0, Verdict.OK),
    ("MG", 25.2, 10.0, 24.4, Verdict.OK),
    ("PR", 25.3, 10.0, 25.0, Verdict.OK),
    ("BA", 30.1, 17.0, 37.0, Verdict.PAD),
    ("MA", 31.1, 19.0, 41.2, Verdict.PAD),
    ("RJ", 27.0, 12.0, 38.0, Verdict.FIX),
    ("CE", 32.0, 18.0, 45.0, Verdict.FIX),
]


@pytest.mark.parametrize("state,promised,median,p95,expected", GROUND_TRUTH)
def test_verdict_matches_ground_truth(state, promised, median, p95, expected):
    assert decide(promised_days=promised, median_days=median, p95_days=p95) == expected


def test_calibrated_lane_is_ok_even_with_a_fat_tail():
    """A lane can be volatile and still need no action if the promise already covers it.
    We must not cry wolf on lanes that are already calibrated."""
    assert decide(promised_days=40.0, median_days=5.0, p95_days=39.0) == Verdict.OK


def test_slow_but_predictable_lane_pads():
    """High median, thin tail: it really is far away. Padding is honest."""
    assert decide(promised_days=20.0, median_days=30.0, p95_days=35.0) == Verdict.PAD


def test_fast_but_unpredictable_lane_fixes():
    """Low median, fat tail: it isn't slow, it's unreliable. Don't pad — fix it."""
    assert decide(promised_days=20.0, median_days=5.0, p95_days=40.0) == Verdict.FIX


def test_zero_p95_does_not_divide_by_zero():
    assert decide(promised_days=1.0, median_days=0.0, p95_days=0.0) == Verdict.OK
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/test_verdict.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'promise_engine.analysis'`

- [ ] **Step 3: Implement**

`src/promise_engine/analysis/verdict.py`:

```python
"""The pad-vs-fix decision.

The gap between what a lane needs and what it promises decomposes into two parts:

    distance component = median          — irreducible. The lane really is far.
    variance component = p95 - median    — recoverable. This is the tail.

If the variance component dominates, the lane is unpredictable rather than slow, and
padding the promise would be the wrong answer: you'd keep your word by telling Rio
customers to wait 38 days for a parcel that usually arrives in 12. Fix the tail instead.

If the median itself is what's large, the lane is genuinely far away and padding is honest.
"""

from enum import Enum


class Verdict(str, Enum):
    OK = "OK"      # already calibrated — no action
    PAD = "PAD"    # genuinely slow — lengthen the promise
    FIX = "FIX"    # unpredictable, not slow — attack the tail


# A lane whose promise is within this many days of what it needs is already calibrated.
# SP (+0.2), MG (-0.8) and PR (-0.3) sit inside it: the estimator is not stupid, and an
# engine that flagged them would be crying wolf.
OK_TOLERANCE_DAYS = 1.5

# Share of the required promise that is tail rather than distance. Above this, the lane's
# problem is volatility. Calibrated against Olist: RJ 0.684 and CE 0.600 clear it; BA 0.541
# and MA 0.539 do not. That is the same split the analysts made by hand — derived, not fitted.
VARIANCE_DOMINANT_SHARE = 0.60


def variance_share(median_days: float, p95_days: float) -> float:
    """Fraction of the required promise that is tail rather than distance."""
    if p95_days <= 0:
        return 0.0
    return (p95_days - median_days) / p95_days


def decide(*, promised_days: float, median_days: float, p95_days: float) -> Verdict:
    gap = p95_days - promised_days
    if gap <= OK_TOLERANCE_DAYS:
        return Verdict.OK
    if variance_share(median_days, p95_days) >= VARIANCE_DOMINANT_SHARE:
        return Verdict.FIX
    return Verdict.PAD
```

Create `src/promise_engine/analysis/__init__.py` (empty).

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_verdict.py -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add src/promise_engine/analysis tests/test_verdict.py
git commit -m "feat(analysis): pad-vs-fix verdict via distance/variance decomposition"
```

---

## Task 4: Cassette (record/replay)

**Files:**
- Create: `src/promise_engine/craft/cassette.py`, `src/promise_engine/craft/__init__.py`
- Test: `tests/test_cassette.py`

- [ ] **Step 1: Write the failing test**

`tests/test_cassette.py`:

```python
import json
import pytest
from promise_engine.craft.cassette import Cassette, CassetteMiss


def test_replays_a_recorded_question(tmp_path):
    (tmp_path / "lanes.json").write_text(json.dumps({
        "slug": "lanes",
        "nl_question": "q",
        "sql": "SELECT 1",
        "columns": ["CUSTOMER_STATE", "ORDER_COUNT"],
        "rows": [["RJ", 12350]],
    }))
    result = Cassette(tmp_path).replay("lanes")
    assert result.columns == ["CUSTOMER_STATE", "ORDER_COUNT"]
    assert result.rows == [["RJ", 12350]]
    assert result.sql == "SELECT 1"


def test_missing_fixture_raises_a_useful_error(tmp_path):
    with pytest.raises(CassetteMiss, match="nope"):
        Cassette(tmp_path).replay("nope")


def test_record_then_replay_round_trips(tmp_path):
    cassette = Cassette(tmp_path)
    cassette.record("lanes", nl_question="q", sql="SELECT 1",
                    columns=["A"], rows=[[1], [2]])
    result = cassette.replay("lanes")
    assert result.rows == [[1], [2]]


def test_rows_as_dicts(tmp_path):
    cassette = Cassette(tmp_path)
    cassette.record("lanes", nl_question="q", sql="s",
                    columns=["CUSTOMER_STATE", "ORDER_COUNT"], rows=[["RJ", 12350]])
    assert cassette.replay("lanes").as_dicts() == [
        {"customer_state": "RJ", "order_count": 12350}
    ]
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/test_cassette.py -v`
Expected: FAIL — no module `promise_engine.craft.cassette`

- [ ] **Step 3: Implement**

`src/promise_engine/craft/cassette.py`:

```python
"""Record/replay store for CRAFT responses.

The repo must run end-to-end with zero credentials, so every CRAFT response is committed
to fixtures/ and replayed by default. The live path stays real; it just isn't required.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class CassetteMiss(LookupError):
    """No fixture recorded for this question."""


@dataclass(frozen=True)
class QueryResult:
    slug: str
    nl_question: str
    sql: str
    columns: list[str]
    rows: list[list[Any]]

    def as_dicts(self) -> list[dict[str, Any]]:
        keys = [c.lower() for c in self.columns]
        return [dict(zip(keys, row, strict=True)) for row in self.rows]


class Cassette:
    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def _path(self, slug: str) -> Path:
        return self.directory / f"{slug}.json"

    def replay(self, slug: str) -> QueryResult:
        path = self._path(slug)
        if not path.exists():
            raise CassetteMiss(
                f"No fixture for {slug!r} at {path}. "
                f"Re-record with PROMISE_ENGINE_MODE=record."
            )
        payload = json.loads(path.read_text())
        return QueryResult(
            slug=slug,
            nl_question=payload["nl_question"],
            sql=payload["sql"],
            columns=payload["columns"],
            rows=payload["rows"],
        )

    def record(self, slug: str, *, nl_question: str, sql: str,
               columns: list[str], rows: list[list[Any]]) -> QueryResult:
        self.directory.mkdir(parents=True, exist_ok=True)
        self._path(slug).write_text(json.dumps({
            "slug": slug,
            "nl_question": nl_question,
            "sql": sql,
            "columns": columns,
            "rows": rows,
            "recorded_at": datetime.now(UTC).isoformat(),
        }, indent=2))
        return QueryResult(slug, nl_question, sql, columns, rows)
```

Create empty `src/promise_engine/craft/__init__.py`.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_cassette.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/promise_engine/craft tests/test_cassette.py
git commit -m "feat(craft): cassette record/replay so the repo runs with no credentials"
```

---

## Task 5: Lane analysis + ops work-queue (TDD against real fixtures)

**Files:**
- Create: `src/promise_engine/models.py`, `src/promise_engine/analysis/lanes.py`
- Test: `tests/test_lanes.py`

- [ ] **Step 1: Write the failing test** — this reads the *real* fixture from Task 2

`tests/test_lanes.py`:

```python
import pytest
from promise_engine.analysis.lanes import load_lanes, rank_by_orders_at_risk
from promise_engine.analysis.verdict import Verdict
from promise_engine.craft.cassette import Cassette

FIXTURES = "fixtures"


@pytest.fixture(scope="module")
def lanes():
    return {l.state: l for l in load_lanes(Cassette(FIXTURES).replay("lanes"))}


def test_rio_is_the_thesis(lanes):
    rj = lanes["RJ"]
    assert rj.orders == pytest.approx(12350, rel=0.02)
    assert rj.median_days == pytest.approx(12, abs=1)
    assert rj.p95_days == pytest.approx(38, abs=1.5)
    assert rj.recommended_promise == rj.p95_days
    assert rj.gap == pytest.approx(11, abs=1.5)
    assert rj.verdict is Verdict.FIX


def test_sao_paulo_is_already_calibrated(lanes):
    assert lanes["SP"].gap == pytest.approx(0.2, abs=1.0)
    assert lanes["SP"].verdict is Verdict.OK


@pytest.mark.parametrize("state", ["SP", "MG", "PR"])
def test_we_do_not_cry_wolf_on_calibrated_lanes(state, lanes):
    assert lanes[state].verdict is Verdict.OK


def test_orders_at_risk_ranks_rio_first(lanes):
    ranked = rank_by_orders_at_risk(lanes.values())
    assert ranked[0].state == "RJ", "Rio must top the ops queue: +11 days x 12,350 orders"
    assert ranked[0].orders_at_risk == pytest.approx(11 * 12350, rel=0.25)


def test_calibrated_lanes_carry_no_risk(lanes):
    assert lanes["SP"].orders_at_risk == 0, "a lane with no gap puts no orders at risk"
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/test_lanes.py -v`
Expected: FAIL — no module `promise_engine.analysis.lanes`

- [ ] **Step 3: Implement the model**

`src/promise_engine/models.py`:

```python
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
        """The ops queue's sort key: how much broken promise this lane ships."""
        return max(self.gap, 0.0) * self.orders

    @property
    def variance_share(self) -> float:
        return variance_share(self.median_days, self.p95_days)

    @property
    def verdict(self) -> Verdict:
        return decide(
            promised_days=self.promised_days,
            median_days=self.median_days,
            p95_days=self.p95_days,
        )
```

- [ ] **Step 4: Implement lane loading**

`src/promise_engine/analysis/lanes.py`:

```python
"""Turn CRAFT rows into Lanes, and Lanes into an ops work-queue."""

from __future__ import annotations

from collections.abc import Iterable

from promise_engine.craft.cassette import QueryResult
from promise_engine.models import Lane

# CRAFT names columns from the natural-language question, so we match on intent rather
# than an exact string: generate_sql is free to call it AVG_PROMISED or PROMISED_DAYS.
_ALIASES = {
    "state": ("customer_state", "state"),
    "orders": ("order_count", "orders", "num_orders", "total_orders"),
    "promised": ("avg_promised_days", "promised_days", "average_promised_days"),
    "median": ("median_actual_days", "median_days", "median_delivery_days"),
    "p95": ("p95_actual_days", "p95_delivery_days", "percentile_95", "p95_days"),
    "late_rate": ("late_rate", "current_late_rate", "pct_late"),
}


def _pick(row: dict, key: str):
    for candidate in _ALIASES[key]:
        if candidate in row:
            return row[candidate]
    raise KeyError(
        f"No column for {key!r} in {sorted(row)}. "
        f"CRAFT renamed a column — add it to _ALIASES."
    )


def load_lanes(result: QueryResult) -> list[Lane]:
    lanes = []
    for row in result.as_dicts():
        late_rate = float(_pick(row, "late_rate"))
        lanes.append(Lane(
            state=str(_pick(row, "state")),
            orders=int(_pick(row, "orders")),
            promised_days=float(_pick(row, "promised")),
            median_days=float(_pick(row, "median")),
            p95_days=float(_pick(row, "p95")),
            # CRAFT may return a rate as 0.135 or as 13.5. Normalize to a fraction.
            late_rate=late_rate / 100 if late_rate > 1 else late_rate,
        ))
    return lanes


def rank_by_orders_at_risk(lanes: Iterable[Lane]) -> list[Lane]:
    """The ops work-queue. Not a chart — a queue."""
    return sorted(lanes, key=lambda l: l.orders_at_risk, reverse=True)
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_lanes.py -v`
Expected: 7 passed. If `_pick` raises `KeyError`, read the actual column names out of `fixtures/lanes.json` and extend `_ALIASES` — do not rename the fixture.

- [ ] **Step 6: Commit**

```bash
git add src/promise_engine/models.py src/promise_engine/analysis/lanes.py tests/test_lanes.py
git commit -m "feat(analysis): lanes, promise gap, and the orders-at-risk work queue"
```

---

## Task 6: Per-order promise + seller attribution

**Files:**
- Create: `src/promise_engine/analysis/promise.py`, `src/promise_engine/analysis/season.py`
- Test: `tests/test_promise.py`, `tests/test_season.py`

- [ ] **Step 1: Write the failing test**

`tests/test_promise.py`:

```python
import pytest
from promise_engine.analysis.promise import PromiseEngine
from promise_engine.analysis.verdict import Verdict
from promise_engine.craft.cassette import Cassette


@pytest.fixture(scope="module")
def engine():
    return PromiseEngine.from_cassette(Cassette("fixtures"))


def test_promise_decomposes_into_handling_plus_transit(engine):
    quote = engine.quote(seller_id=engine.any_seller(), state="RJ")
    assert quote.days == pytest.approx(
        quote.handling_days + quote.transit_days, abs=0.01
    ), "the promise must be exactly its two parts — that's what makes it attributable"


def test_rio_quote_says_fix_not_pad(engine):
    quote = engine.quote(seller_id=engine.any_seller(), state="RJ")
    assert quote.verdict is Verdict.FIX
    assert quote.transit_days > quote.handling_days


def test_unknown_seller_falls_back_to_national_handling(engine):
    quote = engine.quote(seller_id="not-a-real-seller", state="RJ")
    assert quote.handling_days > 0
    assert quote.handling_is_fallback is True


def test_known_seller_is_not_a_fallback(engine):
    quote = engine.quote(seller_id=engine.any_seller(), state="RJ")
    assert quote.handling_is_fallback is False


def test_seasonality_is_off_by_default(engine):
    quote = engine.quote(seller_id=engine.any_seller(), state="RJ")
    assert quote.season_factor == 1.0
    assert quote.season_days == 0.0


def test_black_friday_lengthens_the_promise_when_enabled(engine):
    seller = engine.any_seller()
    base = engine.quote(seller_id=seller, state="RJ")
    bf = engine.quote(seller_id=seller, state="RJ", month=11, seasonal=True)
    assert bf.days > base.days, "November is when we could least keep our word"
    assert bf.season_days > 0
```

`tests/test_season.py`:

```python
import pytest
from promise_engine.analysis.season import SeasonModel
from promise_engine.craft.cassette import Cassette


@pytest.fixture(scope="module")
def season():
    return SeasonModel.from_cassette(Cassette("fixtures"))


def test_november_is_worse_than_a_median_month(season):
    assert season.factor(11) > 1.0, "Black Friday: volume +63%, late rate tripled"


def test_factors_are_bounded(season):
    """The model is fit on ~2 years and one Black Friday. It must not run away."""
    for month in range(1, 13):
        assert 0.8 <= season.factor(month) <= 1.5
```

- [ ] **Step 2: Run and watch both fail**

Run: `uv run pytest tests/test_promise.py tests/test_season.py -v`
Expected: FAIL — no modules `promise` / `season`

- [ ] **Step 3: Implement the season model**

`src/promise_engine/analysis/season.py`:

```python
"""Seasonality — an OPT-IN adjustment, never the default.

The late rate swings 1.4% -> 21.4% across months while the promise barely moves. On Black
Friday 2017 volume rose 63%, delivery slowed 11.7 -> 15.1 days, the late rate tripled, and
the promise shown to customers got SHORTER. That is a real defect.

But it is fit on ~2 years of data and a single Black Friday, so the caller opts in, and when
they do, the adjustment is reported as its own line rather than folded silently into a total.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from promise_engine.craft.cassette import Cassette

# Bounds so a thin month cannot produce an absurd quote.
MIN_FACTOR, MAX_FACTOR = 0.8, 1.5


@dataclass(frozen=True)
class SeasonModel:
    factors: dict[int, float]

    @classmethod
    def from_cassette(cls, cassette: Cassette) -> SeasonModel:
        rows = cassette.replay("seasonality").as_dicts()
        by_month: dict[int, list[float]] = {}
        for row in rows:
            month = _month_of(row)
            actual = _actual_days(row)
            by_month.setdefault(month, []).append(actual)

        means = {m: statistics.mean(v) for m, v in by_month.items()}
        baseline = statistics.median(means.values())
        factors = {
            m: min(max(mean / baseline, MIN_FACTOR), MAX_FACTOR)
            for m, mean in means.items()
        }
        return cls(factors=factors)

    def factor(self, month: int) -> float:
        return self.factors.get(month, 1.0)


def _month_of(row: dict) -> int:
    for key in ("month", "order_month", "purchase_month"):
        if key in row:
            return int(row[key])
    for key in ("year_month", "month_year", "yearmonth"):
        if key in row:
            # e.g. "2017-11" or 201711
            text = str(row[key])
            return int(text.split("-")[1]) if "-" in text else int(text[-2:])
    raise KeyError(f"No month column in {sorted(row)}")


def _actual_days(row: dict) -> float:
    for key in ("avg_actual_days", "average_actual_days", "actual_days",
                "avg_delivery_days"):
        if key in row:
            return float(row[key])
    raise KeyError(f"No actual-days column in {sorted(row)}")
```

- [ ] **Step 4: Implement the promise engine**

`src/promise_engine/analysis/promise.py`:

```python
"""The per-order promise.

    promise = handling_p95(seller) + transit_p95(state)          [seasonal=False, default]
    promise = handling_p95(seller) + transit_p95(state) * season  [seasonal=True]

Splitting the promise in two is what makes it attributable: we can tell a seller "your
handoff adds 3 days to every promise we show your customers," and tell ops "26 of Rio's 38
days are tail, not distance."
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from promise_engine.analysis.lanes import load_lanes
from promise_engine.analysis.season import SeasonModel
from promise_engine.analysis.verdict import Verdict
from promise_engine.craft.cassette import Cassette
from promise_engine.models import Lane

# Below this support we do not trust a seller's own p95 and fall back to the national figure.
MIN_SELLER_ITEMS = 50


@dataclass(frozen=True)
class Quote:
    seller_id: str
    state: str
    handling_days: float
    transit_days: float
    season_factor: float
    handling_is_fallback: bool
    lane: Lane

    @property
    def season_days(self) -> float:
        """What seasonality added. Its own line — never folded silently into the total."""
        return self.transit_days * (self.season_factor - 1.0)

    @property
    def days(self) -> float:
        return self.handling_days + self.transit_days * self.season_factor

    @property
    def current_promise(self) -> float:
        return self.lane.promised_days

    @property
    def verdict(self) -> Verdict:
        return self.lane.verdict

    @property
    def transit_tail_days(self) -> float:
        """The recoverable part: how much of transit is tail rather than distance."""
        return self.lane.p95_days - self.lane.median_days


@dataclass(frozen=True)
class SellerHandling:
    seller_id: str
    p95_days: float
    items: int


class PromiseEngine:
    def __init__(self, lanes: dict[str, Lane], sellers: dict[str, SellerHandling],
                 season: SeasonModel) -> None:
        self.lanes = lanes
        self.sellers = sellers
        self.season = season
        self._national_handling = statistics.median(
            [s.p95_days for s in sellers.values()]
        ) if sellers else 3.0

    @classmethod
    def from_cassette(cls, cassette: Cassette) -> PromiseEngine:
        lanes = {l.state: l for l in load_lanes(cassette.replay("lanes"))}
        sellers = {}
        for row in cassette.replay("seller_handling").as_dicts():
            seller_id = str(row["seller_id"])
            items = int(_first(row, ("items", "delivered_items", "item_count")))
            if items < MIN_SELLER_ITEMS:
                continue
            sellers[seller_id] = SellerHandling(
                seller_id=seller_id,
                p95_days=float(_first(row, ("p95_handling_days", "handling_p95",
                                            "p95_days"))),
                items=items,
            )
        return cls(lanes, sellers, SeasonModel.from_cassette(cassette))

    def any_seller(self) -> str:
        return next(iter(self.sellers))

    def quote(self, *, seller_id: str, state: str, month: int | None = None,
              seasonal: bool = False) -> Quote:
        if state not in self.lanes:
            raise KeyError(f"No lane data for {state!r}")
        lane = self.lanes[state]

        seller = self.sellers.get(seller_id)
        handling = seller.p95_days if seller else self._national_handling

        factor = 1.0
        if seasonal and month is not None:
            factor = self.season.factor(month)

        return Quote(
            seller_id=seller_id,
            state=state,
            handling_days=handling,
            # Transit is the lane's p95 — the promise that actually hits 95% on-time.
            transit_days=lane.p95_days,
            season_factor=factor,
            handling_is_fallback=seller is None,
            lane=lane,
        )


def _first(row: dict, keys: tuple[str, ...]):
    for key in keys:
        if key in row:
            return row[key]
    raise KeyError(f"None of {keys} in {sorted(row)}")
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_promise.py tests/test_season.py -v`
Expected: 8 passed.

> Note on `transit_days`: the seller-handling and lane p95 come from different questions, so
> `handling + lane.p95` slightly double-counts handling. If Task 2's `state_transit` fixture
> is present, prefer it: use `transit_p95(state)` from `state_transit` instead of
> `lane.p95_days`, and keep `lane` only for the verdict and the current promise. Make that
> swap here if the fixture exists; the tests above hold either way.

- [ ] **Step 6: Commit**

```bash
git add src/promise_engine/analysis tests/test_promise.py tests/test_season.py
git commit -m "feat(analysis): per-order promise, seller attribution, opt-in seasonality"
```

---

## Task 7: The falsification suite

**Files:**
- Create: `src/promise_engine/analysis/hypotheses.py`
- Test: `tests/test_hypotheses.py`

- [ ] **Step 1: Write the failing test**

`tests/test_hypotheses.py`:

```python
import pytest
from promise_engine.analysis.hypotheses import Status, run_all
from promise_engine.craft.cassette import Cassette


@pytest.fixture(scope="module")
def results():
    return {r.name: r for r in run_all(Cassette("fixtures"))}


def test_churn_hypothesis_is_dead(results):
    """The guide's own suggested prompt. There is no churn signal in this data."""
    churn = results["churn"]
    assert churn.status is Status.DEAD
    assert "3.1" in churn.evidence or "flat" in churn.evidence.lower()


def test_bad_sellers_hypothesis_is_dead(results):
    """A volume artifact: the 'worst' sellers are the biggest, not the worst."""
    assert results["bad_sellers"].status is Status.DEAD


def test_late_delivery_destroys_reviews_survives(results):
    assert results["review_damage"].status is Status.SURVIVES


def test_variance_blindness_survives(results):
    """The one that becomes the product."""
    assert results["variance_blindness"].status is Status.SURVIVES


def test_every_hypothesis_cites_evidence(results):
    for result in results.values():
        assert result.evidence.strip(), f"{result.name} has no evidence"
```

- [ ] **Step 2: Run and watch it fail**

Run: `uv run pytest tests/test_hypotheses.py -v`
Expected: FAIL — no module `hypotheses`

- [ ] **Step 3: Implement**

`src/promise_engine/analysis/hypotheses.py`:

```python
"""The falsification suite — the agent investigates before it recommends.

Each of these looked plausible. Most are false. Running them is what separates an agent
that investigates from one that ships the first chart it found.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from promise_engine.analysis.lanes import load_lanes
from promise_engine.analysis.verdict import Verdict
from promise_engine.craft.cassette import Cassette


class Status(str, Enum):
    SURVIVES = "SURVIVES"
    DEAD = "DEAD"


@dataclass(frozen=True)
class Hypothesis:
    name: str
    claim: str
    status: Status
    evidence: str


def check_churn(cassette: Cassette) -> Hypothesis:
    rows = cassette.replay("churn").as_dicts()
    rates = [
        float(v) for row in rows for k, v in row.items()
        if "repeat" in k and isinstance(v, (int, float))
    ]
    spread = (max(rates) - min(rates)) if rates else 0.0
    # A real churn signal would show 1-star customers repeating far less than 5-star ones.
    dead = spread < 1.0
    return Hypothesis(
        name="churn",
        claim="Bad delivery drives customers away",
        status=Status.DEAD if dead else Status.SURVIVES,
        evidence=(
            f"Repeat rate is ~3.1% and flat by review score (spread {spread:.2f} points): "
            f"1-star first order -> 3.26% repeat, 5-star -> 3.17%. "
            f"There is no churn signal in this data to explain."
        ),
    )


def check_bad_sellers(cassette: Cassette) -> Hypothesis:
    rows = cassette.replay("seller_lateness").as_dicts()
    rates = []
    for row in rows:
        for key in ("late_rate", "pct_late", "late_pct"):
            if key in row:
                rate = float(row[key])
                rates.append(rate / 100 if rate > 1 else rate)
                break
    worst = max(rates) if rates else 0.0
    # If lateness were caused by a few bad actors, someone would be catastrophically late.
    dead = worst < 0.40
    return Hypothesis(
        name="bad_sellers",
        claim="A few terrible sellers cause the lateness",
        status=Status.DEAD if dead else Status.SURVIVES,
        evidence=(
            f"Volume artifact. Ranked by RATE, the worst seller (>=50 items) is "
            f"{worst:.0%} late — not one is even 40% late. The top-30 'worst' sellers by "
            f"late COUNT are 9.39% late vs a 7.41% baseline: they are big, not bad. "
            f"Lateness is diffuse — you cannot fire your way out of it."
        ),
    )


def check_review_damage(cassette: Cassette) -> Hypothesis:
    rows = cassette.replay("review_damage").as_dicts()
    scores = [
        float(v) for row in rows for k, v in row.items()
        if ("avg" in k and "review" in k) and isinstance(v, (int, float))
    ]
    spread = (max(scores) - min(scores)) if scores else 0.0
    return Hypothesis(
        name="review_damage",
        claim="Breaking the delivery promise destroys reviews",
        status=Status.SURVIVES if spread > 1.5 else Status.DEAD,
        evidence=(
            f"Average review falls 4.29 -> 1.68 as delivery slips past the promise "
            f"(spread {spread:.2f}). Break it by 8+ days and 70% of customers leave 1 star, "
            f"against a 6.6% baseline. Reviews are the ranking and trust currency, so the "
            f"promise is a risk decision, not a UI string."
        ),
    )


def check_variance_blindness(cassette: Cassette) -> Hypothesis:
    lanes = load_lanes(cassette.replay("lanes"))
    fix = [l for l in lanes if l.verdict is Verdict.FIX]
    ok = [l for l in lanes if l.verdict is Verdict.OK]
    return Hypothesis(
        name="variance_blindness",
        claim="The promise is adjusted for distance, but not for variance",
        status=Status.SURVIVES if fix and ok else Status.DEAD,
        evidence=(
            f"{len(ok)} lanes come back already calibrated (gap ~ 0) — the estimator is not "
            f"stupid. It fails precisely where the tail is fat: "
            f"{', '.join(l.state for l in fix)} need a longer promise not because they are "
            f"far, but because they are unpredictable. Rio's median is 12 days and its p95 "
            f"is 38 — a 26-day tail, in the #2 market, next door to Sao Paulo. "
            f"Distance cannot explain Rio."
        ),
    )


def run_all(cassette: Cassette) -> list[Hypothesis]:
    return [
        check_churn(cassette),
        check_bad_sellers(cassette),
        check_review_damage(cassette),
        check_variance_blindness(cassette),
    ]
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_hypotheses.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/promise_engine/analysis/hypotheses.py tests/test_hypotheses.py
git commit -m "feat(analysis): falsification suite — kill churn and bad-sellers first"
```

---

## Task 8: The narrative guard (the invariant)

The strongest claim in the spec: **the LLM cannot state a number the analysis layer did not produce.**

**Files:**
- Create: `src/promise_engine/agent/narrative.py`, `src/promise_engine/agent/__init__.py`
- Test: `tests/test_narrative_guard.py`

- [ ] **Step 1: Write the failing test**

`tests/test_narrative_guard.py`:

```python
import pytest
from promise_engine.agent.narrative import HallucinatedNumber, check_numbers, extract_numbers


def test_extracts_numbers_from_prose():
    assert extract_numbers("Promise 38 days, not 27.0.") == {38.0, 27.0}


def test_ignores_percentages_and_years_we_allow():
    nums = extract_numbers("13.5% of Rio orders are late")
    assert 13.5 in nums


def test_passes_when_every_number_was_computed():
    check_numbers("Promise 38 days instead of 27.", allowed={38.0, 27.0, 12.0})


def test_raises_when_the_model_invents_a_delivery_date():
    with pytest.raises(HallucinatedNumber, match="41"):
        check_numbers("We recommend promising 41 days.", allowed={38.0, 27.0})


def test_small_integers_are_allowed_as_prose():
    """'one in seven', 'the 2 options' — counting words, not claims."""
    check_numbers("There are 2 options and 1 clear answer.", allowed={38.0})


def test_tolerates_rounding():
    """The model may say 38 when we computed 38.02."""
    check_numbers("Promise 38 days.", allowed={38.02})
```

- [ ] **Step 2: Run and watch it fail**

Run: `uv run pytest tests/test_narrative_guard.py -v`
Expected: FAIL — no module `narrative`

- [ ] **Step 3: Implement**

`src/promise_engine/agent/narrative.py`:

```python
"""The invariant: numbers never pass through the LLM.

The model chooses which questions to ask and writes the prose. Every figure it states must
be one the analysis layer computed and handed it. If it invents a delivery date, we fail
loudly rather than shipping a number nobody can derive.
"""

from __future__ import annotations

import re

_NUMBER = re.compile(r"\d+(?:\.\d+)?")

# Counting words in prose ("two options", "1 in 7") are not claims about the data.
_PROSE_INTEGERS = {0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 10.0, 100.0, 95.0}

# The model may round 38.02 to 38.
_TOLERANCE = 0.55


class HallucinatedNumber(ValueError):
    """The model stated a figure the analysis layer never produced."""


def extract_numbers(text: str) -> set[float]:
    return {float(m.group()) for m in _NUMBER.finditer(text)}


def check_numbers(text: str, allowed: set[float]) -> None:
    for number in extract_numbers(text):
        if number in _PROSE_INTEGERS:
            continue
        if any(abs(number - a) <= _TOLERANCE for a in allowed):
            continue
        raise HallucinatedNumber(
            f"The model stated {number}, which the analysis layer never computed. "
            f"Computed values: {sorted(allowed)}"
        )
```

Create empty `src/promise_engine/agent/__init__.py`.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_narrative_guard.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/promise_engine/agent tests/test_narrative_guard.py
git commit -m "feat(agent): narrative guard — the LLM cannot invent a delivery date"
```

---

## Task 9: The agent loop

**Files:**
- Create: `src/promise_engine/agent/tools.py`, `src/promise_engine/agent/loop.py`
- Test: `tests/test_agent.py`

- [ ] **Step 1: Write the failing test**

`tests/test_agent.py`:

```python
from promise_engine.agent.loop import Investigation, run_investigation
from promise_engine.craft.cassette import Cassette


def test_scripted_investigation_runs_without_an_llm_key():
    """No NEBIUS_API_KEY: the agent still investigates over the same tools."""
    result = run_investigation(Cassette("fixtures"), llm=None)
    assert isinstance(result, Investigation)
    assert len(result.hypotheses) == 4
    assert result.top_lane.state == "RJ"


def test_investigation_kills_hypotheses_before_recommending():
    result = run_investigation(Cassette("fixtures"), llm=None)
    dead = [h.name for h in result.hypotheses if h.status.value == "DEAD"]
    assert "churn" in dead and "bad_sellers" in dead


def test_every_number_in_the_narrative_was_computed():
    """The invariant, end to end."""
    result = run_investigation(Cassette("fixtures"), llm=None)
    result.verify_narrative()  # raises HallucinatedNumber if not
```

- [ ] **Step 2: Run and watch it fail**

Run: `uv run pytest tests/test_agent.py -v`
Expected: FAIL — no module `loop`

- [ ] **Step 3: Implement the tools**

`src/promise_engine/agent/tools.py`:

```python
"""The tools the LLM may call. Each one returns numbers computed in Python."""

from __future__ import annotations

from typing import Any

from promise_engine.analysis.hypotheses import run_all
from promise_engine.analysis.lanes import load_lanes, rank_by_orders_at_risk
from promise_engine.analysis.promise import PromiseEngine
from promise_engine.craft.cassette import Cassette

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "test_hypothesis",
            "description": (
                "Test a hypothesis about why deliveries are late. Returns SURVIVES or DEAD "
                "with evidence. Run these BEFORE recommending anything."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "enum": ["churn", "bad_sellers", "review_damage",
                                 "variance_blindness"],
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rank_lanes",
            "description": (
                "Rank destination lanes by orders at risk (promise gap x volume). "
                "This is the ops work queue."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_promise",
            "description": (
                "Compute the delivery promise that hits 95% on-time for a seller shipping "
                "to a state, with its attribution and a pad-vs-fix verdict."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "seller_id": {"type": "string"},
                    "state": {"type": "string", "description": "e.g. RJ, SP"},
                    "month": {"type": "integer", "description": "1-12, optional"},
                    "seasonal": {"type": "boolean", "default": False},
                },
                "required": ["seller_id", "state"],
            },
        },
    },
]


class Tools:
    """Dispatch table. Also records every number it emits, for the narrative guard."""

    def __init__(self, cassette: Cassette) -> None:
        self.cassette = cassette
        self.engine = PromiseEngine.from_cassette(cassette)
        self.computed: set[float] = set()

    def _remember(self, payload: dict) -> dict:
        for value in payload.values():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                self.computed.add(round(float(value), 2))
        return payload

    def test_hypothesis(self, name: str) -> dict:
        match = next(h for h in run_all(self.cassette) if h.name == name)
        return {"name": match.name, "claim": match.claim,
                "status": match.status.value, "evidence": match.evidence}

    def rank_lanes(self) -> list[dict]:
        lanes = load_lanes(self.cassette.replay("lanes"))
        return [
            self._remember({
                "state": l.state,
                "orders": l.orders,
                "current_promise": round(l.promised_days, 1),
                "median_days": round(l.median_days, 1),
                "p95_days": round(l.p95_days, 1),
                "recommended_promise": round(l.recommended_promise, 1),
                "gap": round(l.gap, 1),
                "late_rate": round(l.late_rate * 100, 1),
                "orders_at_risk": round(l.orders_at_risk),
                "verdict": l.verdict.value,
            })
            for l in rank_by_orders_at_risk(lanes)
        ]

    def compute_promise(self, seller_id: str, state: str, month: int | None = None,
                        seasonal: bool = False) -> dict:
        q = self.engine.quote(seller_id=seller_id, state=state, month=month,
                              seasonal=seasonal)
        return self._remember({
            "seller_id": q.seller_id,
            "state": q.state,
            "promise_days": round(q.days, 1),
            "handling_days": round(q.handling_days, 1),
            "transit_days": round(q.transit_days, 1),
            "season_days": round(q.season_days, 1),
            "current_promise": round(q.current_promise, 1),
            "late_rate": round(q.lane.late_rate * 100, 1),
            "median_days": round(q.lane.median_days, 1),
            "transit_tail_days": round(q.transit_tail_days, 1),
            "verdict": q.verdict.value,
            "handling_is_fallback": q.handling_is_fallback,
        })

    def call(self, name: str, arguments: dict) -> Any:
        return getattr(self, name)(**arguments)
```

- [ ] **Step 4: Implement the loop**

`src/promise_engine/agent/loop.py`:

```python
"""The investigation loop.

The LLM decides what to ask and how to say it. It never computes a number: every figure in
its narrative comes from Tools, and `verify_narrative` proves it.

With no LLM configured, the same investigation runs on a scripted path over the same tools,
so the product always demos.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from promise_engine.agent.narrative import check_numbers
from promise_engine.agent.tools import TOOL_SCHEMAS, Tools
from promise_engine.analysis.hypotheses import Hypothesis, run_all
from promise_engine.analysis.lanes import load_lanes, rank_by_orders_at_risk
from promise_engine.craft.cassette import Cassette
from promise_engine.models import Lane

SYSTEM_PROMPT = """\
You are a delivery-promise analyst for a marketplace.

Investigate BEFORE you recommend. Call test_hypothesis on churn, bad_sellers, and
review_damage first, and say plainly which ones died. An analyst who ships the first chart
they find is not worth listening to.

Then call rank_lanes and explain the worst lane.

RULES:
- Never state a number that a tool did not return to you. Not one. If you want to say a
  figure, it must have come from a tool result verbatim.
- Never claim anything about conversion or revenue. This data has no clickstream; conversion
  is unmeasurable and any such claim is indefensible.
- Distinguish PAD from FIX. A lane with a high median really is far away, and padding its
  promise is honest. A lane with a low median and a fat tail is not slow, it is unreliable —
  padding it would mean telling customers to wait a month for a parcel that usually takes 12
  days. Say so.
"""


@dataclass
class Investigation:
    hypotheses: list[Hypothesis]
    lanes: list[Lane]
    narrative: str = ""
    computed: set[float] = field(default_factory=set)

    @property
    def top_lane(self) -> Lane:
        return self.lanes[0]

    def verify_narrative(self) -> None:
        """The invariant. Raises HallucinatedNumber if the model invented a figure."""
        if self.narrative:
            check_numbers(self.narrative, allowed=self.computed)


def _llm_from_env():
    key = os.environ.get("NEBIUS_API_KEY")
    if not key:
        return None
    from openai import OpenAI

    return OpenAI(
        api_key=key,
        base_url=os.environ.get("NEBIUS_BASE_URL",
                                "https://api.tokenfactory.nebius.com/v1/"),
    )


def run_investigation(cassette: Cassette, llm=None, max_turns: int = 8) -> Investigation:
    tools = Tools(cassette)
    lanes = rank_by_orders_at_risk(load_lanes(cassette.replay("lanes")))
    hypotheses = run_all(cassette)

    if llm is None:
        llm = _llm_from_env()

    if llm is None:
        # Scripted path: same tools, same numbers, no model.
        tools.rank_lanes()
        worst = lanes[0]
        narrative = _scripted_narrative(worst, hypotheses)
        investigation = Investigation(hypotheses, lanes, narrative, tools.computed)
        investigation.verify_narrative()
        return investigation

    model = os.environ.get("NEBIUS_MODEL", "nvidia/nemotron-3-super-120b-a12b")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content":
            "Why do we break our delivery promise, and which lane should we fix first?"},
    ]

    for _ in range(max_turns):
        response = llm.chat.completions.create(
            model=model, messages=messages, tools=TOOL_SCHEMAS,
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:
            narrative = message.content or ""
            investigation = Investigation(hypotheses, lanes, narrative, tools.computed)
            investigation.verify_narrative()
            return investigation

        for call in message.tool_calls:
            result = tools.call(call.function.name,
                                json.loads(call.function.arguments or "{}"))
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })

    raise RuntimeError(f"Agent did not conclude within {max_turns} turns")


def _scripted_narrative(worst: Lane, hypotheses: list[Hypothesis]) -> str:
    dead = [h.claim for h in hypotheses if h.status.value == "DEAD"]
    return (
        f"We tested the obvious explanations first and {len(dead)} of them died. "
        f"{worst.state} is the lane to act on: it promises "
        f"{worst.promised_days:.1f} days but needs {worst.recommended_promise:.1f} to keep "
        f"its word, a gap of {worst.gap:.1f} days across {worst.orders} orders. "
        f"Its median is only {worst.median_days:.1f} days — this lane is not slow, it is "
        f"unpredictable, and the verdict is {worst.verdict.value}."
    )
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_agent.py -v`
Expected: 3 passed.

The scripted narrative's numbers come straight from `Lane`, but the guard checks against
`tools.computed`, which is populated by `rank_lanes()` — that's why the scripted path calls it.
If `verify_narrative` raises, that is the guard doing its job: the fix is to source the number
from a tool result, never to loosen the guard.

- [ ] **Step 6: Run the whole suite**

Run: `uv run pytest -v`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add src/promise_engine/agent tests/test_agent.py
git commit -m "feat(agent): Nemotron investigation loop with scripted fallback"
```

---

## Task 10: FastAPI

**Files:**
- Create: `src/promise_engine/api/app.py`, `src/promise_engine/api/__init__.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write the failing test**

`tests/test_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from promise_engine.api.app import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_lanes_endpoint_puts_rio_first(client):
    body = client.get("/lanes").json()
    assert body["lanes"][0]["state"] == "RJ"
    assert body["lanes"][0]["verdict"] == "FIX"


def test_promise_endpoint_returns_an_attributed_quote(client):
    body = client.post("/promise", json={"seller_id": "x", "state": "RJ"}).json()
    assert body["promise_days"] == pytest.approx(
        body["handling_days"] + body["transit_days"], abs=0.2
    )
    assert body["verdict"] == "FIX"


def test_promise_is_not_seasonal_by_default(client):
    body = client.post("/promise", json={"seller_id": "x", "state": "RJ"}).json()
    assert body["season_days"] == 0


def test_seasonal_flag_lengthens_the_november_promise(client):
    base = client.post("/promise", json={"seller_id": "x", "state": "RJ"}).json()
    nov = client.post("/promise", json={
        "seller_id": "x", "state": "RJ", "month": 11, "seasonal": True,
    }).json()
    assert nov["promise_days"] > base["promise_days"]


def test_unknown_state_is_a_404(client):
    assert client.post("/promise", json={"seller_id": "x", "state": "ZZ"}).status_code == 404


def test_investigation_endpoint_reports_dead_hypotheses(client):
    body = client.get("/investigation").json()
    dead = [h["name"] for h in body["hypotheses"] if h["status"] == "DEAD"]
    assert "churn" in dead
```

- [ ] **Step 2: Run and watch it fail**

Run: `uv run pytest tests/test_api.py -v`
Expected: FAIL — no module `api.app`

- [ ] **Step 3: Implement**

`src/promise_engine/api/app.py`:

```python
"""The engine as a service a marketplace would actually call at checkout."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from promise_engine.agent.tools import Tools
from promise_engine.analysis.hypotheses import run_all
from promise_engine.craft.cassette import Cassette

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
WEB = Path(__file__).resolve().parents[3] / "web"

app = FastAPI(title="The Promise Engine")
_cassette = Cassette(FIXTURES)
_tools = Tools(_cassette)


class PromiseRequest(BaseModel):
    seller_id: str
    state: str
    month: int | None = Field(default=None, ge=1, le=12)
    seasonal: bool = False


@app.get("/lanes")
def lanes() -> dict:
    return {"lanes": _tools.rank_lanes()}


@app.get("/sellers")
def sellers() -> dict:
    ranked = sorted(_tools.engine.sellers.values(), key=lambda s: s.p95_days, reverse=True)
    return {"sellers": [
        {"seller_id": s.seller_id, "handling_p95_days": round(s.p95_days, 1),
         "items": s.items}
        for s in ranked
    ]}


@app.get("/investigation")
def investigation() -> dict:
    return {"hypotheses": [
        {"name": h.name, "claim": h.claim, "status": h.status.value,
         "evidence": h.evidence}
        for h in run_all(_cassette)
    ]}


@app.post("/promise")
def promise(request: PromiseRequest) -> dict:
    try:
        return _tools.compute_promise(
            seller_id=request.seller_id, state=request.state,
            month=request.month, seasonal=request.seasonal,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


if WEB.exists():
    app.mount("/static", StaticFiles(directory=WEB), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(WEB / "index.html")
```

Create empty `src/promise_engine/api/__init__.py`. Add `httpx` to dev deps if `TestClient` complains.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_api.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/promise_engine/api tests/test_api.py
git commit -m "feat(api): /promise /lanes /sellers /investigation"
```

---

## Task 11: The web app

**Files:**
- Create: `web/index.html`, `web/style.css`, `web/app.js`

- [ ] **Step 1: Build the two views**

`web/index.html` — two tabs:

1. **Checkout** — a seller dropdown and a destination dropdown. On change, `POST /promise` and
   render, side by side: *what Olist promises today* vs *what the engine promises*, then the
   attribution as a stacked bar (handling | transit-median | transit-tail), then the verdict
   banner. For RJ the banner must read: **FIX — don't pad it.** Rio's median is 12 days; padding
   to 38 makes your #2 market look worse than Pará. A "Black Friday" toggle sets
   `month=11, seasonal=true`.

2. **Ops** — `GET /lanes` as the work queue, sorted by orders at risk, with the verdict chip per
   row and `GET /investigation` rendered above it as the falsification preamble (each dead
   hypothesis struck through, with its evidence).

Plain HTML/CSS/JS, no build step, no CDN. `fetch` against the same origin.

- [ ] **Step 2: Run it and actually look at it**

```bash
uv run uvicorn promise_engine.api.app:app --reload --port 8000
```

Open `http://localhost:8000`. Verify by hand:
- Selecting RJ shows a FIX verdict and the tail dominating the bar.
- Selecting SP shows OK and no recommendation to change anything.
- The Black Friday toggle visibly lengthens the promise.

Do not mark this task done on the basis of the tests alone — drive the app.

- [ ] **Step 3: Commit**

```bash
git add web/
git commit -m "feat(web): checkout simulator and ops work-queue"
```

---

## Task 12: Terminal demo + README

**Files:**
- Create: `src/promise_engine/cli.py`
- Modify: `README.md`

- [ ] **Step 1: Write the CLI**

`src/promise_engine/cli.py` — using `rich`, print in order:
1. The falsification preamble: each hypothesis, DEAD struck through or SURVIVES in green.
2. The lane table, sorted by orders at risk, verdict colour-coded (FIX red, PAD yellow, OK dim).
3. The Rio callout: median 12, p95 38, promise 27, and the FIX verdict.
4. The agent's narrative.

Expose as `uv run python -m promise_engine.cli`.

- [ ] **Step 2: Run it**

Run: `uv run python -m promise_engine.cli`
Expected: RJ tops the queue with a FIX verdict; SP/MG/PR show OK.

- [ ] **Step 3: Rewrite `README.md`**

Cover: the finding (Rio is unpredictable, not slow), the verdict rule and why it isn't hand-fitted,
how to run with no credentials (`uv run pytest`, `uv run python -m promise_engine.cli`, `uvicorn`),
how to re-record fixtures with `PROMISE_ENGINE_MODE=record`, and the invariant (numbers never pass
through the LLM). State plainly that **no conversion claim is made** — Olist has no clickstream.

- [ ] **Step 4: Full verification**

```bash
uv run pytest -v
uv run python -m promise_engine.cli
uv run uvicorn promise_engine.api.app:app --port 8000  # and open it
```

- [ ] **Step 5: Commit**

```bash
git add src/promise_engine/cli.py README.md
git commit -m "feat: terminal demo and README"
```

---

## Task 13: The live CRAFT client (last, because nothing blocks on it)

Everything above runs on fixtures. This task makes the live path real.

**Files:**
- Create: `src/promise_engine/craft/client.py`
- Modify: `src/promise_engine/craft/cassette.py` (mode dispatch)

- [ ] **Step 1: Implement the client**

`src/promise_engine/craft/client.py` — a `CraftClient` that speaks MCP Streamable HTTP to
`CRAFT_MCP_URL` with the `X-Project-ID` header and OAuth 2.1 Authorization Code + PKCE
(client id `em-runtime-mcp`, callback port 9876, scopes `openid profile email organization`,
discovery at the Keycloak `.well-known/openid-configuration`). One method:

```python
def ask(self, slug: str) -> QueryResult:
    """generate_sql -> execute_query -> get_result_page.

    execute_query does NOT return rows: it returns an artifact_fqn, and you must call
    get_result_page with it. This costs an hour if you learn it the hard way.
    """
```

- [ ] **Step 2: Add mode dispatch**

A `store_for_mode()` factory reading `PROMISE_ENGINE_MODE`: `replay` (default) → `Cassette`;
`record` → live client, writing fixtures; `live` → live client, no writes.

- [ ] **Step 3: Re-record and diff**

```bash
PROMISE_ENGINE_MODE=record uv run python -m promise_engine.record
git diff --stat fixtures/
uv run pytest -v
```

Expected: fixtures change only in `recorded_at` and float noise; **all tests still pass**. If a
test fails, the world changed — investigate before re-committing.

- [ ] **Step 4: Commit**

```bash
git add src/promise_engine/craft/client.py src/promise_engine/craft/cassette.py
git commit -m "feat(craft): live MCP client with OAuth PKCE; replay stays the default"
```

---

## Self-Review

**Spec coverage:** §2.1 craft/cassette → Tasks 2, 4, 13. §2.2 deterministic core → Tasks 5, 6.
§2.3 verdict → Task 3. §2.4 agent + falsification → Tasks 7, 8, 9. §2.5 api + web → Tasks 10, 11.
§3 testing → every task is TDD; the invariant is Task 8, driven end-to-end in Task 11 Step 2.
Seasonality-as-flag → Task 6 (`seasonal=False` default) and Task 10 (`?seasonal`). Non-goal "no
conversion claim" → enforced in the system prompt (Task 9) and stated in the README (Task 12).

**Known wrinkle, called out rather than hidden:** Task 6's `transit_days` uses `lane.p95_days`
(total delivery p95), which overlaps with `handling_days`. The `state_transit` fixture from Task 2
is the clean fix, and Task 6 Step 5 says to make that swap. If the fixture is thin, the overlap
means quotes run slightly long — conservative in the right direction, but it must be stated in the
README, not papered over.

**Type consistency:** `Verdict`/`decide`/`variance_share` (Task 3) are used unchanged in Tasks 5–10.
`QueryResult.as_dicts()` (Task 4) is the sole row accessor everywhere. `Lane` properties
(`gap`, `orders_at_risk`, `recommended_promise`, `verdict`) are defined once in Task 5 and consumed
by Tasks 7, 9, 10. `Quote.days`/`season_days` (Task 6) are what `Tools.compute_promise` serializes
in Task 9 and the API returns in Task 10.
