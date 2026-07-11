# The Promise Engine

An agent that decides the delivery date a marketplace can actually keep — built on real
Olist (Brazilian e-commerce) data, recorded once via CRAFT and replayed forever after, so the
whole thing runs with **zero credentials**.

## The finding

Every marketplace shows a delivery date at checkout. Break it and reviews collapse: early
deliveries average 4.29/5 (6.6% 1-star); deliveries 8–15 days late average 1.68/5 (70%
1-star). So the promise isn't a cosmetic string — it's a risk decision made on every order.

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
every number it returns into a `computed` set. Before any narrative — LLM-written or scripted
— is accepted, `agent.narrative.check_numbers()` walks the text and raises
`HallucinatedNumber` if it states a figure that no tool ever produced (allowing only small
rounding drift and common prose numbers like "1 in 7"). `run_investigation` calls this guard
itself before returning an `Investigation`, so a model that invents a delivery estimate fails
the build loudly instead of reaching a customer-facing promise. With no `NEBIUS_API_KEY` set,
the same guard runs against a scripted narrative built from the same tool calls — the product
demos identically either way.

**No conversion or revenue claim is made anywhere** — in code, prompts, or UI copy. Olist has
no clickstream data (no sessions, page views, or cart events) in this dataset, so conversion
is unmeasurable here, and any such claim would be indefensible. The case for action rests
entirely on orders at risk and the measured damage to reviews.

## Running it (zero credentials required)

```bash
uv run pytest                                              # 112 tests, all against replayed fixtures
uv run python -m promise_engine.cli                        # falsification preamble + ops queue + Rio callout + narrative
uv run uvicorn promise_engine.api.app:app --port 8000       # API + web app at http://localhost:8000
```

Everything above replays fixtures already committed in `fixtures/*.json` — no API keys, no
network calls. Setting `NEBIUS_API_KEY` (see `.env.example`) switches the investigation from
a scripted narrative to a live LLM (Nebius Token Factory, OpenAI-compatible) driving the same
tools; the narrative guard applies identically to both paths.

### The web app

Two tabs, served from `web/` (plain HTML/CSS/JS, no build step, no CDN, dark-mode aware):

- **Checkout** — pick a seller and destination state, optionally toggle "Black Friday
  (November)", and see the current promise vs. the engine's promise side by side, a stacked
  bar decomposing the promise into seller handling / lane transit / lane tail, and a
  color-coded verdict banner (FIX / PAD / OK) with a borderline caveat where relevant.
- **Ops** — the falsification preamble (which hypotheses died, which survived, with evidence)
  followed by the ops work-queue ranked by orders at risk, with Rio on top.

## Architecture

```
fixtures/*.json                         (recorded once from CRAFT, replayed forever)
   -> craft/cassette.py                 record/replay store
   -> analysis/{lanes,promise,season,verdict,hypotheses}.py   the analysis layer
   -> agent/tools.py                    Tools wraps the analysis layer, records every number
   -> agent/loop.py                     run_investigation(): LLM or scripted, same tools either way
   -> agent/narrative.py                the guard: no number in prose that no tool produced
   -> api/app.py                        FastAPI: /lanes /sellers /investigation /promise /states
   -> web/                              the checkout + ops UI
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
