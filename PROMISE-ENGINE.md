# The Promise Engine

**An agent that decides the delivery date a marketplace shows at checkout — one that it can
actually keep.**

Dataset: `brazilian-e-commerce-5f7bc95c` (Olist, real Brazilian marketplace data).
Every number below is verified against the live data via the CRAFT MCP.

---

## The problem

Every marketplace shows you a delivery date. Getting it wrong is expensive:

| Delivery vs. promise | Avg review | % 1-star |
| --- | --- | --- |
| Early | 4.29 | 6.6% |
| 1–3 days late | 3.29 | 25% |
| 8–15 days late | **1.68** | **70%** |

**Break the promise by 8+ days and 70% of customers leave 1 star.** On a marketplace, reviews are
the ranking and trust currency — so the delivery promise is not a cosmetic UI string, it's a
risk decision made 100,000 times a year.

Olist's promise is **distance-aware but blind to two things that actually determine whether it
gets kept.**

---

## Defect 1 — blind to *variance* (where)

The promise scales with how **far** a lane is, not how **unpredictable** it is.

| State | Orders | Promised | Median actual | **p95 actual** | Late rate | **Gap** |
| --- | --- | --- | --- | --- | --- | --- |
| MG | 11,354 | 25.2d | 10d | 24.4d | 5.6% | **−0.8** ✅ |
| PR | 4,923 | 25.3d | 10d | 25.0d | 5.0% | **−0.3** ✅ |
| SP | 40,494 | 19.8d | 7d | 20.0d | 5.9% | **+0.2** ✅ |
| BA | 3,256 | 30.1d | 17d | 37.0d | 14.0% | +6.9 |
| MA | 717 | 31.1d | 19d | 41.2d | 19.7% | +10.1 |
| **RJ** | **12,350** | **27.0d** | **12d** | **38.0d** | **13.5%** | **+11.0** 🚨 |
| CE | 1,279 | 32.0d | 18d | 45.0d | 15.3% | **+13.0** 🚨 |

*(Gap = the promise needed to hit 95% on-time, minus the promise actually made.)*

### Read Rio carefully — it's the whole thesis

**Rio's median delivery is 12 days. Its p95 is 38 days.**

Rio is **not slow** — São Paulo's median is 7. Rio is **wildly unpredictable**: a 26-day tail.
Olist promises 27 days, so it **breaks its word to ~1 in 7 Rio customers** — in its **#2 market**
(12,350 orders, ~13% of volume) sitting **right next to São Paulo**.

Distance explains Maranhão and Pará. **Distance cannot explain Rio.**

And note SP, MG, PR come back **already calibrated** (gap ≈ 0). The estimator isn't stupid — it
works fine where the lane is stable, and **fails precisely where the tail is fat.**

---

## Defect 2 — blind to *time* (when)

| Month | Orders | Actual days | Promised | Late rate |
| --- | --- | --- | --- | --- |
| Oct 2017 | 4,478 | 11.7 | 23.7d | 5.3% |
| **Nov 2017 — Black Friday** | **7,288** | **15.1** | **23.2d** | **14.3%** 🚨 |
| Feb 2018 | 6,555 | 16.9 | 25.2d | 16.0% |
| **Mar 2018** | 7,003 | 16.2 | 22.7d | **21.4%** 🚨 |
| Jun 2018 | 6,096 | 9.2 | 28.4d | **1.4%** ✅ |

**Late rate swings 1.4% → 21.4% — a 15× range. The promise barely moves (20–28 days).**

Black Friday: volume **+63%**, delivery slows 11.7 → 15.1 days, late rate **triples** — and the
promise shown to customers actually got **shorter** (23.7 → 23.2d).

> **Olist made a harder promise exactly when it was least able to keep it.**

---

## What the agent does

**Promise = seller handling p95 + lane transit p95, adjusted for season.**

### Surface 1 — Checkout
At checkout you know the **seller** and the **destination**, so the promise is per-order:

> **Order → Rio de Janeiro.**
> Current promise: **27 days** → you will break it **13.5%** of the time.
> To hit 95% on-time: promise **38 days**.
> Median is only **12 days** — this lane isn't slow, it's *unpredictable*. **The tail is the
> problem.**
> ⚠️ **Don't just pad it — fix it.** Padding Rio to 38 days makes your #2 market look worse
> than Pará.

### Surface 2 — Ops work-queue
Rank lanes by **promise gap × volume** = orders at risk. Rio tops it (+11 days × 12,350 orders).
That's a work queue, not a chart.

### Surface 3 — Seller scorecards (falls out of the decomposition, free)
Because the promise is split into handling + transit, the engine can **attribute**:

> *"38 days — because this seller takes 5 days to hand off to the carrier **and** the Rio lane
> has a 26-day tail."*

Which becomes a product Olist could sell to its sellers: **"Your handling time adds 3 days to
every promise we show your customers."** (Handling ranges **2.1 → 5.0 days** across sellers.)

### The judgement that makes it an agent, not a query
Every risky lane has exactly two options, and the agent **decides**:

- **Pad the promise** → you keep your word, but you look slow.
- **Fix the tail** (carrier, handoff, routing) → you keep your word *and* stay fast.

For **Pará**, padding is honest — it really is far away.
For **Rio**, padding is absurd — 38 days to a neighbouring state. **So: fix it.**

That distinction is the agent's call, and it's what separates this from a SELECT.

---

## ⚠️ The one claim never to make

**Never say "a tighter promise lifts conversion."**

Olist has **no clickstream** — no sessions, no page views, no cart events. Conversion is
**unmeasurable** in this data, and a judge can puncture it in one question.

Claim only what's supported: **service level, broken promises, and the 1-star reviews they cause.**

---

## Credibility: what we tested and threw away

Run these first — they take seconds and they *earn* the recommendation:

| Hypothesis | Verdict |
| --- | --- |
| "Bad delivery drives churn" *(the guide's suggested prompt)* | ❌ **DEAD.** Repeat rate **3.12%**, flat by review score: 1-star → 3.26%, 5-star → 3.17%. No churn signal exists. |
| "Late delivery destroys reviews" | ✅ **TRUE.** 4.29 → 1.68; 1-star 6.6% → 70%. |
| "A few terrible sellers cause it" | ❌ **DEAD — volume artifact.** The top-30 "worst" sellers are 9.39% late vs 7.41% baseline. By *rate*, **no seller is even 40% late.** Lateness is diffuse. |
| "The promise is a dumb flat buffer" | ❌ **DEAD.** It *is* distance-adjusted (SP 20d, PA 38d). |
| **"It's adjusted for distance but not variance or load"** | 🏆 **SURVIVES → the product.** |

This is the two-minute preamble, **not** the product. It proves we didn't ship the first chart we
found.

---

## Build

```
checkout request (seller, destination, date)
   │
agent  →  Nebius Token Factory (Nemotron-3 Super 120B, function calling)
       →  CRAFT MCP: generate_sql → execute_query → get_result_page
       →  promise = handling_p95 + transit_p95, season-adjusted
       →  judgement: pad, or fix?
       →  ops queue ranked by gap × volume
```

**No hand-written SQL** — everything through `generate_sql`.

### Verified NL questions (feed to `generate_sql` verbatim)

Schema arg for all:
`{"schema_name": "BRAZILIAN_E_COMMERCE", "schema_fqn": "brazilian-e-commerce-5f7bc95c.BRAZILIAN_E_COMMERCE.BRAZILIAN_E_COMMERCE"}`

**CORE — this is the product:**
> *"For delivered orders, group by customer_state (only states with at least 500 orders). For each
> state compute: the order count, the average promised days (purchase to estimated delivery), the
> median actual delivery days, the 95th percentile of actual delivery days, and the current late
> rate. Then compute a recommended promise equal to the 95th percentile of actual delivery days,
> and the difference between that recommended promise and the current average promised days.
> Order by that difference ascending."*

**SEASONALITY (~20 min — best story-per-minute in the build):**
> *"For delivered orders, group by the year and month of order_purchase_timestamp and show the
> number of orders, the average actual delivery days, the average promised days, and the late
> rate. Only months with at least 500 orders, ordered chronologically."*

**SELLER DECOMPOSITION (stretch — makes it per-order):**
> *"For each seller with at least 50 delivered items, compute the 95th percentile of seller
> handling days (order_approved_at to order_delivered_carrier_date). Separately, for each
> customer_state, compute the 95th percentile of carrier transit days
> (order_delivered_carrier_date to order_delivered_customer_date)."*

**CREDIBILITY (fast):**
> *"Using OLIST_CUSTOMERS.customer_unique_id as the true person, how many distinct people are
> there, how many placed more than one order, and what is the overall repeat purchase rate? Then,
> for customers whose FIRST order received a given review score (1 to 5), what percentage went on
> to place another order?"*

> *"Bucket delivered orders by how many days late they were versus the estimated delivery date
> (early, on time, 1-3 days late, 4-7 days late, 8-15 days late, more than 15 days late) and for
> each bucket show the number of orders, the average review score, and the percentage of reviews
> that are 1 star."*

### Gotchas (each costs ~20 min if you hit it cold)

- **`execute_query` does NOT return rows** — it returns an `artifact_fqn`; call `get_result_page`
  with it.
- **`sample_data` wants a 3-part name** (`DB.SCHEMA.TABLE`), *not* the 4-part FQN in the docs.
- **Olist dates are VARCHAR** → `TRY_TO_TIMESTAMP` (CRAFT handles this).
- **Nebius is OpenAI-compatible** — just change `base_url`.

### Cut list, in order
1. Voice / ElevenLabs — **cut.**
2. Web UI → terminal output is fine, arguably better.
3. Seller decomposition → state-level still works.
4. Charts → the table *is* the story.

> **If you're behind at the 1-hour mark, stop building and rehearse.** The core query plus a clear
> Rio narrative beats a half-built agent you can't drive.

---

## The demo (5 min)

1. *"Every marketplace shows a delivery date. Break it by 8 days and 70% of customers leave 1 star."*
2. *"We checked the obvious theories. Churn? Doesn't exist — 3.12%, flat. Bad sellers? A volume
   artifact — nobody's even 40% late. A dumb flat buffer? No — it's distance-adjusted."*
3. *"What it's **not** adjusted for is **variance**. Watch Rio."*
4. **"Rio's median is 12 days. Its p95 is 38. It's not slow — it's unpredictable. We promise 27,
   so we break our word to 1 in 7 customers — in our #2 market, right next to São Paulo."**
5. *"And it's blind to **time**. On Black Friday volume rose 63%, delivery slowed 3.5 days, the
   late rate **tripled** — and the promise we showed customers got **shorter**."*
6. *"So the engine sets a promise that actually hits 95% on-time — by lane **and** by season — and
   ranks the lanes worth fixing. For Rio it says: **don't pad. Fix.**"*
7. *"São Paulo, Minas and Paraná come back **already calibrated**. We're not crying wolf — we're
   pointing at the three lanes and the two months that actually matter."*

---

## Why it scores

**CRAFT depth 30% · Insight quality 30% · Agent architecture 20% · Story clarity 20%**

- **Insight (30%)** — an operational decision with a work-queue attached. The median-vs-p95 split
  (*Rio is unpredictable, not slow*) is genuinely non-obvious, and the Black Friday inversion is
  the kind of finding an ops lead would act on Monday.
- **CRAFT depth (30%)** — multi-table joins, percentile aggregation, all via `generate_sql`.
- **Architecture (20%)** — the agent *investigates before it recommends*, discards its own failed
  hypotheses, then makes a judgement call (pad vs. fix) per lane.
- **Story (20%)** — *"Rio is next door to São Paulo and we break our promise to 1 in 7 of its
  customers."*
