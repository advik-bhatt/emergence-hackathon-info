# THE PROMISE ENGINE — build plan (~2 hours)

> **An agent that decides what delivery date to show the customer at checkout — and tells
> operations which lanes are broken.**

Dataset: `brazilian-e-commerce-5f7bc95c` (Olist). Rubric:
**CRAFT depth 30% · Insight quality 30% · Agent architecture 20% · Story clarity 20%**

This is a **real system a marketplace would actually run.** It fires on every order, it changes
what the customer sees, and it produces an ops work-queue. It is not a dashboard and not a
"here's an interesting chart" demo.

**Everything below is verified against live data.** You are wiring, not discovering.

---

## The problem (in one sentence)

**Olist's delivery promise scales with *distance* but not with *reliability* — so it badly
under-protects the lanes that are unpredictable, and 70% of very-late orders turn into 1-star
reviews.**

## The core finding

For each state: what Olist promises, versus what it would need to promise to actually hit a
**95% on-time** target (the p95 of real delivery time).

| State | Orders | Promised | Median actual | **p95 actual** | Late rate | **Promise gap** |
| --- | --- | --- | --- | --- | --- | --- |
| MG | 11,354 | 25.2d | 10d | 24.4d | 5.6% | **−0.8** ✅ calibrated |
| PR | 4,923 | 25.3d | 10d | 25.0d | 5.0% | **−0.3** ✅ calibrated |
| SP | 40,494 | 19.8d | 7d | 20.0d | 5.9% | **+0.2** ✅ calibrated |
| RS | 5,344 | 29.2d | 13d | 33.0d | 7.2% | +3.8 |
| BA | 3,256 | 30.1d | 17d | 37.0d | 14.0% | +6.9 |
| PA | 946 | 37.8d | 21d | 46.8d | 12.4% | +9.0 |
| MA | 717 | 31.1d | 19d | 41.2d | 19.7% | +10.1 |
| **RJ** | **12,350** | **27.0d** | **12d** | **38.0d** | **13.5%** | **+11.0** 🚨 |
| CE | 1,279 | 32.0d | 18d | 45.0d | 15.3% | **+13.0** 🚨 |

### Read Rio carefully — it's the whole story

**Rio's median delivery is 12 days. Its p95 is 38 days.** It is *not slow* (São Paulo's median
is 7). It is **wildly unpredictable** — a 26-day tail. Olist promises 27 days, so 13.5% of Rio
orders break the promise. To genuinely hit 95% on-time there, you'd have to promise **38 days**.

**And Rio is 12,350 orders — the #2 market, ~13% of all volume, sitting right next to São Paulo.**
Distance explains Maranhão and Pará. **Distance cannot explain Rio.** It's a variance problem.

Meanwhile MG, PR and SP are *already* well calibrated (gap ≈ 0). So this isn't "Olist is dumb" —
their estimator works fine where the lane is stable, and fails exactly where the tail is fat.

---

## The SECOND axis: the promise is blind to *time* too

Same defect, different dimension. Verified:

| Month | Orders | Actual days | Promised | Late rate |
| --- | --- | --- | --- | --- |
| Oct 2017 | 4,478 | 11.7 | 23.7d | 5.3% |
| **Nov 2017 (Black Friday)** | **7,288** | **15.1** | **23.2d** | **14.3%** 🚨 |
| Feb 2018 | 6,555 | 16.9 | 25.2d | 16.0% |
| **Mar 2018** | 7,003 | 16.2 | 22.7d | **21.4%** 🚨 |
| Jun 2018 | 6,096 | 9.2 | 28.4d | **1.4%** ✅ |

**The late rate swings 1.4% → 21.4% — a 15× range. The promise barely moves (20–28 days).**

Black Friday is the money example: volume **+63%**, actual delivery slows 11.7 → 15.1 days, late
rate **triples** — and the promise shown to customers actually went **down** (23.7 → 23.2d).
**Olist made a harder promise exactly when it was least able to keep it.**

> **The engine answers *where* AND *when*:**
> *"Same order, same lane. In June: promise 20 days. On Black Friday: promise 28 — or you break
> 1 in 7."*

---

## What the agent DOES (the product)

Two surfaces, one engine:

### 1. Checkout — "what date do we show this customer?"
Input: destination state (and seller, if you have time). Output: the promise that hits the
target service level, plus honesty about it.

> **Order → Rio de Janeiro.**
> Current promise: **27 days** → you will break it **13.5%** of the time.
> To hit 95% on-time: promise **38 days**.
> Median is only **12 days** — this lane isn't slow, it's *unpredictable*. The tail is the
> problem. **Recommendation: don't just pad it — fix it. Padding Rio to 38 days makes your #2
> market look worse than Pará.**

### 2. Ops — "which lanes do we fix, and in what order?"
Rank lanes by **promise gap × volume** = orders at risk. Rio tops it: +11 days of gap on 12,350
orders. That's the work queue. It is a *decision*, not a chart.

### 3. Seller scorecards — free, once you decompose the promise
Split the promise into **seller handling p95 + lane transit p95**. Now the engine can *attribute*:

> *"38 days, because this seller takes 5 days to hand off to the carrier **and** the Rio lane has
> a 26-day tail."*

That attribution is what turns a number into a decision — and it becomes a product Olist could
sell to its sellers: **"Your handling time adds 3 days to every promise we show your customers."**
Seller handling ranges **2.1 → 5.0 days** across the late-rate buckets, so this is real signal.

### The lever the agent surfaces
Every risky lane has exactly two options, and the agent makes the trade explicit:
- **Pad the promise** → you keep your word, but you look slow and uncompetitive.
- **Fix the tail** (carrier, handoff, routing) → you keep your word *and* stay fast.

For Rio, padding is absurd (38 days for a neighbouring state), so the answer is *fix it*. For
Pará, padding is honest — it really is far away. **That distinction is the agent's judgement,
and it's what makes this more than a query.**

## ⚠️ The one claim you must NOT make

**Never say "a tighter promise lifts conversion."** Olist has **no clickstream** — no sessions,
no cart events. Conversion is **unmeasurable** in this data and a judge will puncture it in one
question. Claim only what's supported: *service level, broken promises, and the 1-star reviews
they cause.*

---

## Why it scores

- **Insight quality (30%)** — a real operational decision with a work-queue attached. The
  median-vs-p95 split (Rio is unpredictable, not slow) is genuinely non-obvious.
- **CRAFT depth (30%)** — multi-table joins, percentile aggregation, all through `generate_sql`.
  **No hand-written SQL.**
- **Agent architecture (20%)** — the agent *investigates before it recommends*: it tests and
  discards the obvious explanations (below), then makes a judgement call (pad vs. fix) per lane.
- **Story clarity (20%)** — "Rio is next door to São Paulo and we break our promise to 1 in 7 of
  its customers."

### The investigation that backs it (keep this — it's the credibility)
Run these first; they take seconds and they *earn the right* to the recommendation:
- ❌ **"Bad delivery drives churn."** Repeat rate is **3.12%**, flat by review score (1-star →
  3.26%, 5-star → 3.17%). No churn signal exists. *(This is the prompt the guide suggests. It's
  a trap.)*
- ✅ **"Lateness destroys reviews."** Avg review **4.29 → 1.68**; 1-star rate **6.6% → 70%**.
- ❌ **"A few terrible sellers cause it."** Volume artifact — the top-30 "worst" sellers are 9.39%
  late vs 7.41% baseline. Checking by *rate*, **no seller is even 40% late.** Lateness is diffuse.
- ❌ **"The promise is a dumb flat buffer."** False — it *is* distance-adjusted (SP 20d, PA 38d).
- 🏆 **What survives:** it's adjusted for distance but **not for variance** → Rio.

Don't make this the *product* — make it the two minutes that prove you didn't just grab the
first chart you saw.

---

## Architecture

```
CLI / simple web form
   │
agent loop  →  Nebius Token Factory (Nemotron-3 Super 120B, function calling)
            →  CRAFT MCP: generate_sql → execute_query → get_result_page
            →  judgement: pad the promise, or fix the lane?
            →  ops work-queue ranked by gap × volume
```

## Verified NL questions — feed to `generate_sql` verbatim

Schema arg for all:
`{"schema_name": "BRAZILIAN_E_COMMERCE", "schema_fqn": "brazilian-e-commerce-5f7bc95c.BRAZILIAN_E_COMMERCE.BRAZILIAN_E_COMMERCE"}`

**THE CORE QUERY (this is the product):**
> *"For delivered orders, group by customer_state (only states with at least 500 orders). For
> each state compute: the order count, the average promised days (purchase to estimated
> delivery), the median actual delivery days, the 95th percentile of actual delivery days, and
> the current late rate. Then compute a recommended promise equal to the 95th percentile of
> actual delivery days, and the difference between that recommended promise and the current
> average promised days. Order by that difference ascending."*

Supporting (the investigation):
1. *"Using OLIST_CUSTOMERS.customer_unique_id as the true person, how many distinct people are
   there, how many placed more than one order, and what is the overall repeat purchase rate?
   Then, for customers whose FIRST order received a given review score (1 to 5), what percentage
   went on to place another order?"*
2. *"Bucket delivered orders by how many days late they were versus the estimated delivery date
   (early, on time, 1-3 days late, 4-7 days late, 8-15 days late, more than 15 days late) and for
   each bucket show the number of orders, the average review score, and the percentage of reviews
   that are 1 star."*
3. *"Among sellers with at least 50 delivered items, bucket them by late rate (under 5%, 5-10%,
   10-20%, 20-40%, over 40%) and show for each bucket the number of sellers, total delivered
   items, total late items, and share of all late items."*

**SEASONALITY (add this — ~20 min, doubles the story):**
> *"For delivered orders, group by the year and month of order_purchase_timestamp and show the
> number of orders, the average actual delivery days, the average promised days, and the late
> rate. Only months with at least 500 orders, ordered chronologically."*

**SELLER DECOMPOSITION (the real upgrade — ~30 min):**
> *"For each seller with at least 50 delivered items, compute the 95th percentile of seller
> handling days (order_approved_at to order_delivered_carrier_date). Separately, for each
> customer_state, compute the 95th percentile of carrier transit days
> (order_delivered_carrier_date to order_delivered_customer_date)."*

Then **promise = seller_handling_p95 + lane_transit_p95**. This is what makes the engine
*per-order* rather than *per-state* — at checkout you know the seller — and it hands you a second
product surface for free (seller scorecards, below).

**Skip:** anything involving freight cost / price optimisation. It drags you back toward
conversion claims the data cannot support.

## Gotchas that cost 20 minutes each

- **`execute_query` does NOT return rows** — it returns an `artifact_fqn`; call
  `get_result_page` with it.
- **`sample_data` wants a 3-part name** (`DB.SCHEMA.TABLE`), not the 4-part FQN the docs claim.
- **Olist dates are VARCHAR** — need `TRY_TO_TIMESTAMP` (CRAFT handles it).
- **Nebius is OpenAI-compatible** — just change `base_url`.

---

## Timeline (~2 hours, hard)

| Time | Do |
| --- | --- |
| **0:00–0:20** | Nebius + CRAFT MCP wired. Prove ONE `generate_sql` → `execute_query` → `get_result_page` round-trip prints rows. |
| **0:20–0:50** | **The core query working end-to-end.** Ship the promise table. This alone is the project. |
| **0:50–1:10** | The agent judgement: for a given state, output current promise / recommended promise / late rate / pad-vs-fix call. |
| **1:10–1:25** | **Seasonality** (one query — the Black Friday line is your best sentence). |
| **1:25–1:35** | Ops work-queue (gap × volume) + the investigation queries as a "how we know" preamble. **Seller decomposition only if you're ahead.** |
| **1:35–1:50** | **Record the demo video while it works.** |
| **1:50–2:00** | Devpost writeup. Buffer. |

### Cut list, in order, without hesitation
1. ~~Voice / ElevenLabs~~ — **cut.** Two hours.
2. Web UI → terminal output is fine, arguably better.
3. Seller-level lanes → state-level is enough.
4. Charts → the table is the story.

> **If you're behind at 1:00, stop building and rehearse.** The core query + a clear Rio
> narrative beats a half-built agent you can't drive.

## The 5-minute demo

1. *"Every marketplace shows you a delivery date. Getting it wrong is expensive — 8+ days late
   and 70% of customers leave 1 star."*
2. *"We checked the obvious theories first. Churn? Doesn't exist — 3.12%, flat. Bad sellers? A
   volume artifact — nobody's even 40% late. A dumb flat buffer? No, it's distance-adjusted."*
3. *"What it's NOT adjusted for is **variance**. Watch Rio."*
4. **"Rio's median is 12 days. Its p95 is 38. It's not slow — it's unpredictable. Olist promises
   27, so we break our word to 1 in 7 customers — in our #2 market, right next to São Paulo."**
5. *"And it's blind to **time** as well as place. On Black Friday, volume jumped 63%, delivery
   slowed by 3.5 days, and the late rate **tripled** — while the promise we showed customers
   actually got **shorter**. We made a harder promise exactly when we were least able to keep it."*
6. *"So the engine sets a promise that actually hits 95% on-time — by lane **and** by season — and
   ranks the lanes worth fixing. For Rio it says **don't pad, fix**: promising 38 days to your
   second-biggest market is not a strategy."*
7. *"São Paulo, Minas, Paraná come back **already calibrated**. We're not crying wolf — we're
   pointing at the three lanes and the two months that actually matter."*

---

## Runner-up (only if Olist collapses)

**Cohort Bias Auditor** (`idc`) — mark a TCGA patient as *imaged* if their `case_barcode` appears
in `DICOM_ALL`; ask who's missing. Imaging rate runs **0% (LAML/leukemia) → 77.5% (KIRC/kidney)**.
IDC is sold as pan-cancer; it's a solid-tumor cohort. Race: **Asian 40.15% vs White 44.95%,
p≈0.016 (real)** — but **Black 44.65% vs White 44.95%, no gap**, so don't overclaim. The caveat is
the feature: LAML's 0% is *medicine, not bias*, and the agent must tell those apart.

## Dead — do not touch

- **`thelook`** — SYNTHETIC. Return rate + margin per customer identical across every channel.
  Any correlation returns null. Also the most crowded dataset.
- **Olist churn** — 3.12%, flat. It's the suggested prompt. It's a trap.
- **Olist conversion** — no clickstream. Unmeasurable.
- **"Blast radius"** on `deps-dev` — literally the project printed next to that pairing in the
  guide. Zero originality.
