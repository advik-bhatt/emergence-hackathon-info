# The Promise Engine

An agent that decides the delivery date a marketplace can actually keep — built on real
Olist (Brazilian e-commerce) data, recorded once via CRAFT and replayed forever after, so the
whole thing runs with **zero credentials**.

## The trap

Every marketplace shows a delivery date at checkout. Break it and reviews collapse — but look
closer at `fixtures/review_damage.json` and a second, uglier fact is sitting right next to it:

| Bucket | Avg review | 1-star |
| --- | --- | --- |
| Early | **4.29** | 6.6% |
| On time | 4.03 | 8.5% |
| 1–3 days late | 3.29 | 25.2% |
| 4–7 days late | 2.10 | 58.5% |
| 8–15 days late | 1.68 | 70.0% |
| 15+ days late | 1.75 | 68.9% |

**Early beats on-time.** Nothing in this dataset penalizes a *longer* promise. So follow the
engine's own logic honestly — set the promise wherever the measured outcome is best — and it
does not stop at p95. If reviews are the only outcome Olist's data can measure (and they are:
there is no clickstream, no sessions, no page views, no cart events), then the
review-maximizing delivery promise is **unbounded**. Promise 60 days to everyone. Every order
lands "early." The late rate falls to zero. Average review climbs to 4.29 and every dashboard
turns green.

`promise_engine.analysis.trap.naive_review_optimum()` computes this for real, off the same
fixture, and states the result plainly: **UNBOUNDED — every additional day of promise is
free, and the data never once says stop.** This is not a hypothetical failure mode; it is the
literal output of optimizing the only metric this dataset can see.

## The refusal

The Promise Engine's defining act is that it proves this and then **declines to recommend
it**. The cost of an unbounded promise — a customer who sees "delivery in 2 months" at
checkout and never orders — is not merely unmeasured in Olist's data, it is **structurally
unmeasurable**: there is no clickstream table to look in. An engine that chases the metric it
can see, all the way to +infinity, is not reasoning about the marketplace — it is guessing
with confidence about the part it can't see.

So the engine will not optimize this metric. It states the naive optimum, refuses it, and
falls back to a criterion that needs none of the missing data:

- **Distance component** (`median`) — irreducible. The lane really is far. **PAD is honest.**
- **Variance component** (`p95 − median`) — recoverable. The lane is unpredictable, not slow.
  **FIX it.**

**To be exact about what this claims and doesn't:** the engine does **not** claim that a long
promise hurts conversion or revenue — that would require data Olist doesn't have, and asserting
it anyway would be exactly the kind of unjustified confidence the refusal exists to avoid. The
claim is the opposite: that cost is *unmeasurable here*, which is precisely why the metric
cannot be optimized and the engine must reason structurally instead.

## The resolution: distance vs. variance

Olist's current promise is distance-aware but variance-blind, and nowhere is that clearer
than **Rio de Janeiro**, Olist's #2 market by order count, sitting right next to São Paulo:

| | Rio de Janeiro | São Paulo (for contrast) |
| --- | --- | --- |
| Median delivery | **12 days** | 7 days |
| p95 delivery | **38 days** | 20 days |
| Current promise | 27 days | 19.8 days |
| Late rate | **13.5%** (~1 in 7 orders) | 5.9% |

**Rio isn't slow, it's unpredictable.** Half of all Rio deliveries land in 12 days, but the
tail runs to 38. Olist promises 27 and breaks its word to 1 in 7 Rio customers. Meanwhile SP,
MG, and PR come back already calibrated (gap within ~1 day) — the estimator isn't stupid, it
fails precisely where the tail is fat.

That's why the engine's verdict for Rio is **FIX** (attack the tail — carrier handoff,
routing, whatever is producing the 26-day spread), not **PAD** (lengthen the promise). Padding
Rio out to 38 days would make Olist's #2 market look worse than a genuinely remote state like
Pará. Nine lanes in this data are genuinely far away and PAD is the honest answer for them;
five are already calibrated (OK); three (RJ, RS, CE) are FIX.

## The verdict rule — and an honest caveat about it

A lane is **FIX** when the gap between what it needs (p95) and what it promises is dominated
by *variance* rather than *distance*: specifically, when the tail (`p95 - median`) is at least
60% of the required promise (`tail_fraction >= 0.60`) and that tail is at least 5 days wide.
Otherwise, if there's a real gap, it's **PAD**. Lanes already within 1.5 days of their p95 are
**OK**.

**0.60 is a chosen operating point, not a natural break in the data.** Sorted by
`tail_fraction`, the lowest FIX (Ceará, 0.600) and the highest PAD (Pernambuco, 0.594) are
0.006 apart — Ceará sits exactly on the line. To make that fragility visible instead of
hiding it, every lane also reports a `flip_distance`: how many days its p95 would have to move
before the verdict flips.

- **Rio's verdict is robust**: flip_distance = 8.1 days. Nothing in a reasonable re-estimation
  changes its FIX call.
- **Ceará's and several other lanes' verdicts are borderline** (CE's flip_distance is just 0.1
  days). The product marks these with an `is_borderline` flag rather than reporting FIX/PAD
  with false confidence — see the caveat chip in the checkout UI and the "(borderline)" marker
  in the CLI/ops table.

## The invariant: numbers never pass through the LLM unchecked

The agent (`promise_engine.agent.loop.run_investigation`) calls tools
(`promise_engine.agent.tools.Tools`) that wrap the analysis layer, and every tool call records
every number it returns into a `computed` set (and a human-readable entry into `Tools.trace`).
This applies to `naive_review_optimum` exactly the same as every other tool: the UNBOUNDED
verdict, the saturation day, and the saturated review score are all recorded before the
narrative is allowed to mention them. Before any narrative — LLM-written or scripted — is
accepted, `agent.narrative.check_numbers()` walks the text and raises `HallucinatedNumber` if
it states a figure that no tool ever produced (allowing only small rounding drift and common
prose numbers like "1 in 7"). `run_investigation` calls this guard itself before returning an
`Investigation`, so a model that invents a delivery estimate — or a made-up day count for how
far it would pad the promise — fails the build loudly instead of reaching a customer-facing
promise. With no `NEBIUS_API_KEY` set, the same guard runs against a scripted narrative built
from the same tool calls — the product demos identically either way.

**No conversion or revenue claim is made anywhere** — in code, prompts, or UI copy. Olist has
no clickstream data (no sessions, page views, or cart events) in this dataset, so conversion
is unmeasurable here, and any such claim would be indefensible. The case for action rests
entirely on orders at risk and the measured damage to reviews.

## Running it (zero credentials required)

```bash
uv run pytest                                              # 112 tests, all against replayed fixtures
uv run python -m promise_engine.cli                        # falsification preamble + THE TRAP + reasoning trace + ops queue + Rio callout + narrative
uv run uvicorn promise_engine.api.app:app --port 8000       # API + web app at http://localhost:8000
```

Everything above replays fixtures already committed in `fixtures/*.json` — no API keys, no
network calls. Setting `NEBIUS_API_KEY` (see `.env.example`) switches the investigation from
a scripted narrative to a live LLM (Nebius Token Factory, OpenAI-compatible) driving the same
tools, including `naive_review_optimum`; the narrative guard applies identically to both paths,
and both paths produce the same 5-step reasoning trace (probe, probe, trap, refusal,
resolution) — the demo cannot fail open even if the live LLM call does.

The CLI prints a dedicated **"The Trap"** section between the falsification preamble and the
ops queue: the review curve at D = 0, 5, 10, 15, 20, 30 (climbing, then flat), the UNBOUNDED
verdict, the refusal panel, and the 5-step reasoning trace so a viewer watching the terminal
sees the agent probe, get trapped, refuse, and resolve, in order.

### The web app

Two tabs, served from `web/` (plain HTML/CSS/JS, no build step, no CDN, dark-mode aware):

- **Checkout** — pick a seller and destination state, optionally toggle "Black Friday
  (November)", and see the current promise vs. the engine's promise side by side, a stacked
  bar decomposing the promise into seller handling / lane transit / lane tail, and a
  color-coded verdict banner (FIX / PAD / OK) with a borderline caveat where relevant.
- **Ops** — a "Live investigation" panel that renders the 5-step reasoning trace sequentially
  (probe / trap / refusal / resolution, ~600ms apart) so it reads as the agent reasoning in
  real time, then **"The Trap"** card (an inline-SVG chart of avg review vs. extra promise
  days, the "+∞" / UNBOUNDED verdict, and the refusal text), then the falsification preamble,
  then the ops work-queue ranked by orders at risk, with Rio on top.

## Architecture

```
fixtures/*.json                         (recorded once from CRAFT, replayed forever)
   -> craft/cassette.py                 record/replay store
   -> analysis/{lanes,promise,season,verdict,hypotheses}.py   the analysis layer
   -> analysis/trap.py                  the naive review-maximizing optimum, and the refusal
   -> agent/tools.py                    Tools wraps the analysis layer, records every number + a call trace
   -> agent/loop.py                     run_investigation(): LLM or scripted, same tools + same 5-step trace either way
   -> agent/narrative.py                the guard: no number in prose that no tool produced
   -> api/app.py                        FastAPI: /lanes /sellers /investigation (+ steps, trap) /promise /states
   -> web/                              the checkout + ops UI (live investigation + trap card)
   -> cli.py                            terminal rendering of the same investigation
```

**All SQL came from CRAFT's `generate_sql`; none was hand-written.** The fixtures in
`fixtures/*.json` are the recorded CRAFT responses (question, generated SQL, columns, rows);
`craft/cassette.py` replays them by slug so the whole pipeline runs offline.

## Known limitation: no TIGHTEN verdict

The verdict rule has three outcomes: FIX (attack the tail), PAD (lengthen the promise), OK
(leave it alone). There is no fourth verdict for **over-promising** — a lane whose promise is
needlessly long relative to what it actually takes. In this data that's not a live problem: the
largest over-promise (`gap` negative, i.e. `promised_days > p95_days`) is only 0.8 days (MG),
well inside the OK tolerance. A fuller product serving other marketplaces or datasets should
add a TIGHTEN verdict for lanes that are meaningfully over-promising, rather than silently
folding them into OK.
