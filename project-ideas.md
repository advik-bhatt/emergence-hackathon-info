# THE FALSIFIER — build plan (2 hours)

> **An agent that tries to kill its own hypotheses, and only reports what survives.**

Dataset: `brazilian-e-commerce-5f7bc95c` (Olist). Rubric:
**CRAFT depth 30% · Insight quality 30% · Agent architecture 20% · Story clarity 20%**

Devpost says *"investigation showcase, not a query competition."* Almost every team will show
an agent that confirms whatever it was pointed at. Ours **disproves three plausible theories on
stage** and lands on the one that survives. That's the whole pitch.

**Everything below is already verified against the live data.** The five NL questions are known
to produce working SQL through `generate_sql`. You are not discovering — you are *wiring*.

---

## The investigation (this is your demo script)

### H1 — "Bad experiences drive customers away." ❌ FALSIFIED
Repeat rate is **3.12%** (2,997 of 96,096 customers). And it's flat by first-order review:
**1-star → 3.26% repeat. 5-star → 3.17%.** A ruined delivery has **zero** effect on return rate.
There is no churn to analyse.
*(This is the prompt the hackathon guide suggests for this dataset. We kill it in 30 seconds.)*

### H2 — "Then late delivery must be what hurts." ✅ SURVIVES
It doesn't cost retention — it costs **reviews**, the marketplace's ranking currency.

| Delivery vs promise | Avg review | % 1-star |
| --- | --- | --- |
| Early | 4.29 | 6.6% |
| 1–3 days late | 3.29 | 25% |
| 8–15 days late | **1.68** | **70%** |

### H3 — "So a few terrible sellers must be causing it." ❌ FALSIFIED
The top-30 sellers by late *count* look guilty — until you check their *rate*: **9.39% late vs
7.41%** baseline. They're not bad, **they're just big.** It was a volume artifact.

Check properly (sellers with ≥50 items, ranked by late **rate**): **not one seller is above 40%
late.** Half of all late items come from the utterly ordinary 5–10% bucket. Lateness is
**diffuse**. There are no villains to fire.

### H4 — "Then the delivery promise must be a dumb flat buffer." ❌ FALSIFIED
It isn't. It **is** distance-adjusted: São Paulo is promised ~20 days, Pará ~38.

### 🏆 H5 — What actually survives: **Rio de Janeiro is a broken lane.**

| State | Orders | Promised | Actual | Slack | Late rate |
| --- | --- | --- | --- | --- | --- |
| MA | 717 | 31.1d | 21.5d | 9.6d | 19.7% |
| BA | 3,256 | 30.1d | 19.3d | 10.8d | 14.0% |
| **RJ** | **12,350** | 27.0d | **15.2d** | 11.8d | **13.5%** |
| **SP** | **40,494** | 19.8d | **8.7d** | 11.1d | **5.9%** |
| PR | 4,923 | 25.3d | 11.9d | 13.3d | 5.0% |

**Rio is the 2nd-biggest market (~13% of all orders), sits next door to São Paulo, and is 2.3×
worse — 15.2 days vs 8.7, late 13.5% vs 5.9%.** Distance explains Maranhão. **Distance does not
explain Rio.** It's a broken lane, and unlike the remote states it is big, close, and fixable.

**The mechanic:** Olist's promise scales with *distance* but not with *reliability*. Slack barely
moves (9.6 → 14.4 days) while the late rate moves 4× (5% → 20%). The riskiest lanes get the
*least* buffer. The estimator knows Maranhão is far. It doesn't know Maranhão is **unpredictable**.

### The recommendation
1. **Fix the Rio lane.** Bringing RJ to SP's late rate converts **~900 late orders** into on-time
   ones — and late orders yield 1-star reviews 58–70% of the time.
2. **Make the promise variance-aware, not just distance-aware.** Buffer by lane *reliability*.

### ⚠️ The one thing you must NOT say
**Never claim tighter promises lift conversion.** Olist has **no clickstream** — no sessions, no
cart. That's unmeasurable here and a judge will puncture it. Only claim what's supported.

---

## Architecture

```
CLI  →  agent loop  →  Nebius Token Factory (Nemotron-3 Super 120B, function calling)
                    →  CRAFT MCP: generate_sql → execute_query → get_result_page
                    →  verdict: SUPPORTED / FALSIFIED / INCONCLUSIVE
                    →  next hypothesis
```

The loop is the product. For each hypothesis: **state it → ask CRAFT in English → run it → let
the model rule on its own theory → pivot.** Print every step. The transcript *is* the demo.

**No hand-written SQL.** Every query goes through `generate_sql` — that's the 30% CRAFT-depth
score, and it's free because the questions below already work.

## The five questions (verified — feed these to `generate_sql` verbatim)

Schema arg for all of them:
`{"schema_name": "BRAZILIAN_E_COMMERCE", "schema_fqn": "brazilian-e-commerce-5f7bc95c.BRAZILIAN_E_COMMERCE.BRAZILIAN_E_COMMERCE"}`

1. **H1** — *"Using OLIST_CUSTOMERS.customer_unique_id as the true person, how many distinct
   people are there, how many placed more than one order, and what is the overall repeat purchase
   rate? Then, for customers whose FIRST order received a given review score (1 to 5), what
   percentage went on to place another order?"*
2. **H2** — *"Bucket delivered orders by how many days late they were versus the estimated
   delivery date (early, on time, 1-3 days late, 4-7 days late, 8-15 days late, more than 15 days
   late) and for each bucket show the number of orders, the average review score, and the
   percentage of reviews that are 1 star."*
3. **H3a** — *"Identify the 30 sellers with the most late delivered items, then compare those 30
   against all other sellers on average seller handling days, average carrier transit days, late
   rate, and cross-state share."*
4. **H3b** — *"Among sellers with at least 50 delivered items, bucket them by late rate (under
   5%, 5-10%, 10-20%, 20-40%, over 40%) and show for each bucket the number of sellers, total
   delivered items, total late items, and share of all late items."*
5. **H5** — *"For delivered orders, group by customer_state and compute number of orders, average
   promised days, average actual delivery days, average slack, and late rate. Only states with at
   least 500 orders, ordered by late rate descending."*

## Gotchas that will cost you 20 minutes each

- **`execute_query` does NOT return rows.** It returns an `artifact_fqn` → call
  `get_result_page` with it.
- **`sample_data` wants a 3-part name** (`DB.SCHEMA.TABLE`), not the 4-part FQN the docs claim.
- **Olist timestamps are VARCHAR** — use `TRY_TO_TIMESTAMP` (CRAFT does this for you).
- Nebius is an **OpenAI-compatible endpoint** — point the OpenAI SDK at it, change base_url.

---

## Timeline (2 hours, hard)

| Time | Do |
| --- | --- |
| **0:00–0:20** | Scaffold. Nebius client + CRAFT MCP connected. Prove ONE `generate_sql` → `execute_query` → `get_result_page` round-trip prints rows. |
| **0:20–1:00** | The loop. Hypothesis list → for each: generate_sql, execute, model returns verdict + one-line reason. Print it as a live investigation log. |
| **1:00–1:25** | Final synthesis: model reads all five results and writes the recommendation. One `generate_plotly_chart` of the state table (RJ vs SP). |
| **1:25–1:45** | **Record the demo video.** Do this while it works, not at the end. |
| **1:45–2:00** | Devpost writeup. Buffer. |

### Cut list (in this order, without hesitation)
1. ~~Voice / ElevenLabs~~ — **already cut.** 2 hours. Not negotiable.
2. Web UI → a clean terminal transcript is *better* for this demo anyway.
3. The plotly chart → the state table in monospace is fine.
4. Dynamic hypothesis generation → **hardcode the five hypotheses.** The agent still genuinely
   runs, queries, and rules on each one. That is real. Do not gold-plate this.

> **If you're behind at 1:00, stop building and start rehearsing.** A working 4-hypothesis loop
> you can narrate beats a 6-hypothesis loop you can't demo.

## The 5-minute demo

1. *"The guide told us to investigate churn. So we did — and it doesn't exist."* → H1, 3.12% flat.
2. *"So we asked what late delivery actually costs. Reviews — 70% one-star."* → H2.
3. *"Obvious next move: find the bad sellers. We were wrong — they were just the big sellers."*
   → H3, the volume artifact.
4. *"Wrong again — the promise IS distance-adjusted."* → H4.
5. *"Here's what survived."* → **Rio: next door to São Paulo, 2.3× worse. ~13% of your orders.**
6. *"Our agent disproved three of its own theories to get here. Most agents would have shipped
   the first chart they found."*

---

## Runner-up (only if Olist somehow collapses)

**Cohort Bias Auditor** (`idc`) — mark a TCGA patient as *imaged* if their `case_barcode` appears
in `DICOM_ALL`; ask who's missing. Verified: imaging rate runs **0% (LAML, leukemia) → 77.5%
(KIRC, kidney)**. IDC is sold as pan-cancer; it's a solid-tumor cohort. Race: **Asian 40.15% vs
White 44.95%, p≈0.016 (real)**, but **Black 44.65% vs White 44.95% — no gap** (so don't overclaim).
Caveat that's also the feature: LAML's 0% is *medicine, not bias* — the agent must tell those
apart.

## Dead — do not touch

- **`thelook`** — SYNTHETIC. Return rate and margin per customer identical across every channel.
  Any correlation returns null. Most crowded dataset.
- **Olist churn** — 3.12%, flat. No signal. (It's the suggested prompt. It's a trap.)
- **Olist conversion** — no clickstream exists. Unmeasurable.
- **"Blast radius"** on `deps-dev` — it is *literally the project printed next to that dataset*
  in the guide. Zero originality.
