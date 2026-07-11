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
from promise_engine.craft.cassette import Cassette

HYPOTHESIS_NAMES = ["churn", "bad_sellers", "review_damage", "variance_blindness"]

SYSTEM_PROMPT = """You are the Promise Engine's investigator: you decide whether Olist's \
delivery-promise problem is best explained by bad sellers, customer churn, review damage, or \
an estimator that is blind to variance — and you recommend what ops should do about it.

Rules, in order of importance:
1. Investigate before you recommend. Call test_hypothesis for churn, bad_sellers, and \
review_damage FIRST, and explicitly say which of them died and which survived, with the \
evidence each tool returned. Only after that call rank_lanes and reason about the queue.
2. Never state a number that no tool returned to you. Every day count, percentage, order \
count, or distance in your final answer must trace back to a test_hypothesis, rank_lanes, or \
compute_promise result. If you have not called a tool for a number, do not say it.
3. Never claim anything about conversion or revenue. Olist has no clickstream data here — \
conversion is unmeasurable, and any such claim is indefensible. Talk about late rates, orders \
at risk, and review damage instead.
4. Distinguish PAD from FIX. PAD means the lane is genuinely far away and lengthening the \
promise is honest. FIX means the promise is already failing on tail (variance), not distance \
— padding it further would make an already-fine median look absurd (padding Rio de Janeiro, \
Olist's #2 market, to its 38-day p95 when the median delivery is 12 days would make it look \
worse than a genuinely remote state like Pará). Say explicitly why padding Rio would be wrong.
5. Note which verdicts are robust and which are borderline (is_borderline / flip_distance) — \
a FIX verdict that would flip on a tenth of a day is not the same claim as one that would not \
flip for eight days.

End with a short recommendation for the ops team: what to do first, and why.
"""

INVESTIGATE_PROMPT = (
    "Investigate why Olist's delivery promises are failing and recommend what ops should do "
    "about it. Test the alternative explanations before you conclude anything, then walk the "
    "ops queue and explain the top lane in detail."
)


@dataclass
class Investigation:
    hypotheses: list[dict[str, Any]]
    lanes: list[dict[str, Any]]
    narrative: str
    computed: set[float] = field(default_factory=set)

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


def _scripted_narrative(hypotheses: list[dict[str, Any]], lanes: list[dict[str, Any]]) -> str:
    """Built ONLY from numbers that already passed through `Tools` (the hypotheses and lanes
    calls made just before this runs). No literal figure is retyped from memory here — every
    number below is read straight out of the tool results so it is guaranteed to be in
    `Tools.computed` and pass `verify_narrative()`."""
    by_name = {h["name"]: h for h in hypotheses}
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


def run_investigation(
    cassette: Cassette, llm: Any = None, max_turns: int = 8,
) -> Investigation:
    tools = Tools.from_cassette(cassette)

    # Always run the full falsification suite and the ranked queue ourselves first: this
    # guarantees the preamble is complete and every number in it is recorded, regardless of
    # what an LLM chooses to call (it may call these again; that's harmless).
    hypotheses = [tools.test_hypothesis(name) for name in HYPOTHESIS_NAMES]
    lanes = tools.rank_lanes()

    client = llm if llm is not None else _default_client()
    if client is None:
        narrative = _scripted_narrative(hypotheses, lanes)
    else:
        narrative = _agentic_narrative(client, tools, max_turns)

    investigation = Investigation(
        hypotheses=hypotheses,
        lanes=lanes,
        narrative=narrative,
        computed=tools.computed,
    )
    investigation.verify_narrative()
    return investigation
