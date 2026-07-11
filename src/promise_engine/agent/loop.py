"""The investigation loop.

An LLM (or, absent an API key, a scripted stand-in that calls the exact same tools) walks the
falsification suite before recommending anything, then explains the ops queue in prose. The
one hard rule: every number that reaches the narrative must have come back through `Tools`
first (see agent/tools.py, agent/narrative.py). This module never lets that rule be optional —
`run_investigation` calls `verify_narrative()` itself before returning.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from promise_engine.agent.narrative import HallucinatedNumber, check_numbers
from promise_engine.agent.tools import TOOL_SCHEMAS, Tools
from promise_engine.analysis.trap import review_curve, why_we_refuse
from promise_engine.craft.cassette import Cassette

HYPOTHESIS_NAMES = ["churn", "bad_sellers", "review_damage", "variance_blindness"]

# Hypotheses that die in the probe step vs. the one that survives — used to build the
# 5-beat trace identically whether the narrative came from an LLM or the scripted fallback.
_PROBE_DEAD_NAMES = ["churn", "bad_sellers"]
_PROBE_SURVIVES_NAME = "review_damage"

SYSTEM_PROMPT = """You are the Promise Engine's investigator: you decide whether Olist's \
delivery-promise problem is best explained by bad sellers, customer churn, review damage, or \
an estimator that is blind to variance — and you recommend what ops should do about it.

Rules, in order of importance:
1. Investigate before you recommend. Call test_hypothesis for churn, bad_sellers, and \
review_damage FIRST, and explicitly say which of them died and which survived, with the \
evidence each tool returned.
2. Before recommending anything, call naive_review_optimum. It computes the promise extension \
that maximizes the only outcome this dataset can measure (average review score). It will \
return UNBOUNDED — no bucket in the data penalizes a longer promise, so the review-maximizing \
promise is +infinity. State plainly what it returns. Then REFUSE it: explain that you will not \
recommend it, because the cost of an unbounded promise — a customer who sees "delivery in 2 \
months" and never orders — is not merely unmeasured but structurally unmeasurable in this \
dataset (Olist has no clickstream: no sessions, no page views, no cart events). Because that \
cost cannot be seen, you cannot optimize this metric, and you must reason structurally instead.
3. After refusing the naive optimum, call rank_lanes and use the distance-vs-variance \
criterion to decide what ops should actually do: is a lane's gap DISTANCE (median — \
irreducible, so padding is honest) or VARIANCE (p95 minus median — recoverable, so the lane \
should be fixed instead)?
4. Never state a number that no tool returned to you. Every day count, percentage, order \
count, or distance in your final answer must trace back to a test_hypothesis, \
naive_review_optimum, rank_lanes, or compute_promise result. If you have not called a tool for \
a number, do not say it.
5. Never claim anything about conversion or revenue. Olist has no clickstream data here — \
conversion is unmeasurable, and any such claim is indefensible, even when discussing the \
naive optimum's refusal. The refusal is about an unmeasurable cost, never a claimed effect.
6. Distinguish PAD from FIX. PAD means the lane is genuinely far away and lengthening the \
promise is honest. FIX means the promise is already failing on tail (variance), not distance \
— padding it further would make an already-fine median look absurd (padding Rio de Janeiro, \
Olist's #2 market, to its 38-day p95 when the median delivery is 12 days would make it look \
worse than a genuinely remote state like Pará). Say explicitly why padding Rio would be wrong.
7. Note which verdicts are robust and which are borderline (is_borderline / flip_distance) — \
a FIX verdict that would flip on a tenth of a day is not the same claim as one that would not \
flip for eight days.

End with a short recommendation for the ops team: what to do first, and why.
"""

INVESTIGATE_PROMPT = (
    "Investigate why Olist's delivery promises are failing and recommend what ops should do "
    "about it. Test the alternative explanations before you conclude anything, then walk the "
    "ops queue and explain the top lane in detail."
)


@dataclass(frozen=True)
class Step:
    tool: str
    kind: str  # "probe" | "trap" | "refusal" | "resolution"
    finding: str  # ONE line: what this call established, in plain English


@dataclass
class Investigation:
    hypotheses: list[dict[str, Any]]
    lanes: list[dict[str, Any]]
    narrative: str
    computed: set[float] = field(default_factory=set)
    steps: list[Step] = field(default_factory=list)
    trap: dict[str, Any] | None = None

    @property
    def top_lane(self) -> dict[str, Any] | None:
        return self.lanes[0] if self.lanes else None

    def verify_narrative(self) -> None:
        """Raise HallucinatedNumber if the narrative states a figure no tool produced."""
        check_numbers(self.narrative, allowed=self.computed)


def _default_client():
    """Build an OpenAI-SDK client pointed at Nebius Token Factory, or None if no key is set.
    Absence of a key is not an error — the product must demo without credentials."""
    api_key = os.environ.get("NEBIUS_API_KEY")
    if not api_key:
        return None
    from openai import OpenAI

    return OpenAI(
        api_key=api_key,
        base_url=os.environ.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"),
    )


def _dispatch(tools: Tools, name: str, arguments: dict[str, Any]) -> Any:
    if name == "test_hypothesis":
        return tools.test_hypothesis(**arguments)
    if name == "rank_lanes":
        return tools.rank_lanes()
    if name == "naive_review_optimum":
        return tools.naive_review_optimum()
    if name == "compute_promise":
        return tools.compute_promise(**arguments)
    raise ValueError(f"Unknown tool {name!r}.")


def _agentic_narrative(client, tools: Tools, max_turns: int) -> str:
    model = os.environ.get("NEBIUS_MODEL", "nvidia/nemotron-3-super-120b-a12b")
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": INVESTIGATE_PROMPT},
    ]

    last_content = ""
    for _ in range(max_turns):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMAS,
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            last_content = message.content or last_content
            break

        for call in tool_calls:
            args = json.loads(call.function.arguments or "{}")
            try:
                result = _dispatch(tools, call.function.name, args)
            except Exception as exc:  # noqa: BLE001 - surface the error back to the model
                result = {"error": str(exc)}
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })
        last_content = message.content or last_content
    else:
        # Ran out of turns still calling tools: force a final answer with no more tool use.
        response = client.chat.completions.create(
            model=model, messages=messages, tool_choice="none",
        )
        last_content = response.choices[0].message.content or last_content

    return last_content


def _scripted_narrative(
    hypotheses: list[dict[str, Any]],
    lanes: list[dict[str, Any]],
    optimum: dict[str, Any],
) -> str:
    """Built ONLY from numbers that already passed through `Tools` (the hypotheses, the naive
    optimum, and the lanes calls made just before this runs). No literal figure is retyped from
    memory here — every number below is read straight out of the tool results so it is
    guaranteed to be in `Tools.computed` and pass `verify_narrative()`."""
    died = [h["claim"] for h in hypotheses if h["status"] == "DEAD"]
    survived = [h["claim"] for h in hypotheses if h["status"] == "SURVIVES"]

    top = lanes[0]
    ce = next((lane for lane in lanes if lane["state"] == "CE"), None)
    runners_up = lanes[1:5]

    lines = [
        "Falsification pass, before any recommendation: "
        + "; ".join(f'"{claim}" is DEAD' for claim in died)
        + ". "
        + "; ".join(f'"{claim}" SURVIVES' for claim in survived)
        + ".",
        "",
        (
            "Before recommending anything, we computed the promise that maximizes the only "
            "outcome this dataset measures: average review score. That result is "
            f"{optimum['verdict']}"
        ),
        "",
        (
            "We refuse that optimum. The cost of a long promise is a customer who sees "
            "\"delivery in 2 months\" and never orders — and Olist has no clickstream (no "
            "sessions, no page views, no cart events), so that cost is not merely unmeasured, "
            "it is structurally unmeasurable in this data. We will not optimize a metric whose "
            "downside we cannot see. Instead we fall back to a criterion that needs none of "
            "the missing data: is a lane's gap distance (irreducible — pad it) or variance "
            "(recoverable — fix it)?"
        ),
        "",
        (
            f"The ops queue is topped by {top['state']}: {top['orders']:,} orders, a current "
            f"promise of {top['current_promise']:.0f} days against a median delivery of "
            f"{top['median_days']:.0f} days and a p95 of {top['p95_days']:.0f} days — a gap "
            f"of {top['gap']:.1f} days and a late rate of {top['late_rate']:.1f}%. That puts "
            f"{top['orders_at_risk']:,.0f} orders at risk, more than the next several lanes "
            f"combined ("
            + ", ".join(
                f"{lane['state']} {lane['orders_at_risk']:,.0f}" for lane in runners_up
            )
            + f"). Its verdict is {top['verdict']}: a tail_fraction of {top['tail_fraction']:.2f} "
            f"means most of its required promise is tail rather than distance, so the fix is "
            f"to attack that tail, not to "
            f"pad the promise out to {top['p95_days']:.0f} days — that would make Olist's #2 "
            f"market look slower than lanes that are genuinely far away. This verdict is "
            f"robust: it would take {top['flip_distance']:.1f} days of p95 movement to flip."
        ),
    ]
    if ce is not None and ce["is_borderline"]:
        lines.append(
            f"Ceará's {ce['verdict']} verdict is not nearly as settled: it would flip on just "
            f"{ce['flip_distance']:.1f} days of p95 movement, so treat it as a real "
            f"conclusion but a fragile one."
        )
    lines.append(
        "No claim is made here about conversion or revenue — there is no clickstream data in "
        "this dataset to support one; the case for action rests on orders at risk and the "
        "measured review damage from broken promises alone."
    )
    return "\n".join(lines)


def _build_steps(
    hypotheses: list[dict[str, Any]],
    optimum: dict[str, Any],
    lanes: list[dict[str, Any]],
    review_damage_rows: list[dict[str, Any]],
) -> list[Step]:
    """The same 5-beat trace for both the LLM path and the scripted path: probe (dead), probe
    (survives), trap, refusal, resolution. Built from tool results already on hand, so it
    never has to guess what an LLM chose to call — this module guarantees the shape of the
    demo regardless of what the model does with its turns."""
    by_name = {h["name"]: h for h in hypotheses}
    dead = [by_name[name] for name in _PROBE_DEAD_NAMES if name in by_name]
    survives = by_name.get(_PROBE_SURVIVES_NAME)
    top = lanes[0] if lanes else None

    early_score = next(
        (float(r["avg_review_score"]) for r in review_damage_rows
         if str(r["delivery_bucket"]).lower() == "early"),
        optimum["best_avg_review"],
    )
    worst_score = min(
        (float(r["avg_review_score"]) for r in review_damage_rows), default=early_score,
    )

    steps = [
        Step(
            tool="test_hypothesis",
            kind="probe",
            finding=(
                "; ".join(f'"{h["claim"]}" is DEAD' for h in dead)
                if dead else "no candidate explanations tested"
            ),
        ),
        Step(
            tool="test_hypothesis",
            kind="probe",
            finding=(
                f'"{survives["claim"]}" SURVIVES: broken promises destroy reviews, '
                f"{early_score:.2f} -> {worst_score:.2f}"
                if survives else "review_damage not tested"
            ),
        ),
        Step(
            tool="naive_review_optimum",
            kind="trap",
            finding=(
                "Optimizing the only metric we can measure says: promise +infinity. "
                f"Reviews saturate at {optimum['best_avg_review']:.2f}/5, late rate falls to "
                "zero, and the data never says stop."
            ),
        ),
        Step(
            tool="naive_review_optimum",
            kind="refusal",
            finding=(
                "The agent declines the optimum: the cost of a long promise is unmeasurable "
                "here (no clickstream), so this metric cannot be optimized. Falls back to "
                "the distance-vs-variance criterion instead."
            ),
        ),
        Step(
            tool="rank_lanes",
            kind="resolution",
            finding=(
                f"{top['state']} tops the queue with a tail_fraction of "
                f"{top['tail_fraction']:.2f} — its gap is variance, not distance, so verdict "
                f"is {top['verdict']}: fix the tail, don't pad the promise."
                if top else "no lanes ranked"
            ),
        ),
    ]
    return steps


def run_investigation(
    cassette: Cassette, llm: Any = None, max_turns: int = 8,
) -> Investigation:
    tools = Tools.from_cassette(cassette)

    # Always run the full falsification suite, the naive optimum, and the ranked queue
    # ourselves first: this guarantees the preamble/trap/queue are complete and every number
    # in them is recorded, regardless of what an LLM chooses to call (it may call these
    # again; that's harmless) — and it guarantees the 5-step trace is identical whether or
    # not an LLM is available.
    hypotheses = [tools.test_hypothesis(name) for name in HYPOTHESIS_NAMES]
    optimum = tools.naive_review_optimum()
    lanes = tools.rank_lanes()

    client = llm if llm is not None else _default_client()
    if client is None:
        narrative = _scripted_narrative(hypotheses, lanes, optimum)
    else:
        narrative = _agentic_narrative(client, tools, max_turns)

    review_damage_rows = cassette.replay("review_damage").as_dicts()
    steps = _build_steps(hypotheses, optimum, lanes, review_damage_rows)
    curve = review_curve(cassette)
    trap = {
        **optimum,
        "curve": [
            {
                "extra_days": point.extra_days,
                "avg_review": round(point.avg_review, 3),
                "one_star_rate": round(point.one_star_rate, 4),
                "late_rate": round(point.late_rate, 4),
            }
            for point in curve
        ],
        "why_we_refuse": why_we_refuse(),
    }

    investigation = Investigation(
        hypotheses=hypotheses,
        lanes=lanes,
        narrative=narrative,
        computed=tools.computed,
        steps=steps,
        trap=trap,
    )
    investigation.verify_narrative()
    return investigation
