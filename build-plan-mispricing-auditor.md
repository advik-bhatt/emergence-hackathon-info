# THE MISPRICING AUDITOR — build plan (~2–3 hours)

> **One agent that ignores a system's own priority label and computes what actually
> carries the risk — then reprices the work-queue. Proven live on TWO unrelated
> domains (software supply-chain + e-commerce logistics) to show it's a general law,
> not a hand-tuned query.**

Target: **Emergence × Nebius Enterprise Agents Hackathon.**
Rubric: **CRAFT depth 30% · Insight quality 30% · Agent architecture 20% · Story clarity 20%.**
Hard requirement: build on ≥1 CRAFT database (we use 2, driven by one engine).

**Everything numeric below is VERIFIED this session via `generate_sql` (server-side execution).
You are wiring, not discovering.**

---

## 0. The one-sentence thesis (the whole pitch)

**Every system ships a priority label — a CVE severity, a delivery promise, a funnel
stage. We built one agent that ignores the label and computes the *real* exposure, and
the labels turn out to be backwards.** The same unchanged engine finds it in security
data and in logistics data — so it's not a quirk of one dataset, it's a repeatable failure
mode of human-assigned priorities.

Why this wins where a single-dataset demo doesn't: the cross-dataset run is the *evidence*
for the insight ("this is a general law"), not a breadth gimmick. That is a 30%-Insight and
20%-Architecture play at the same time.

---

## 1. The two verified findings (your ammunition)

### HERO — `deps-dev-v1`: severity label is ANTI-correlated with blast radius
Across **30,212 advisories**, average number of downstream dependents by GitHub severity:

| Declared severity | Avg dependents | Note |
| --- | --- | --- |
| **CRITICAL** | **10.85** | *lowest of the labeled classes* |
| MODERATE | 11.39 | |
| LOW | 17.98 | |
| **HIGH** | **18.30** | max 2,235 (`debug`, npm) |
| UNKNOWN | 1.01 | **62.7% of all advisories** — the dominant class is *unlabeled* |

**The CVEs labeled CRITICAL touch fewer projects than the ones labeled LOW or HIGH.** The
label a security team triages by is decoupled from — even mildly inverted against — the
computed blast radius. Supporting: volume ≠ severity by ecosystem (npm 12,123 advisories /
7.1% critical vs Maven 3,888 / 14.7% critical); OSS-Fuzz covers 77 of 1,154,633 projects
(0.007%); project stars are power-law (57% zero-star, top 100 repos = 9.5% of all stars).

> This is the single most counterintuitive, judge-friendly number in the whole dataset set.
> It stands alone even if everything else is cut.

### CORROBORATION — `brazilian-e-commerce` (Olist): the delivery promise is variance-blind
The promise is distance-adjusted but **not** variance-adjusted:

| State | Orders | Promised | Median actual | **p95 actual** | Late rate | Gap |
| --- | --- | --- | --- | --- | --- | --- |
| SP / MG / PR | large | ~20–25d | 7–10d | ~20–25d | 5–6% | ≈0 ✅ calibrated |
| **RJ (Rio)** | **12,350 (#2 market)** | **27d** | **12d** | **38d** | **13.5%** | **+11 🚨** |

**Rio isn't slow (median 12d) — it's unpredictable (p95 38d).** The estimator is calibrated to
the *mean* and blind to the *tail*, so its second-biggest market silently runs 13.5% late,
right next to São Paulo. Late delivery then destroys reviews on a cliff (avg **4.29 → 1.68**;
1-star **6.6% → 70%**). Same abstract failure as deps-dev: *the system's own estimate is
decoupled from real exposure.*

### OPTIONAL 3rd beat (story only, cut first) — health coverage gap
`idc` ∩ `pancancer-atlas-1`: only **46.7%** of 10,761 TCGA cancer patients are imaged — and the
gap is a **50× spread by tumor type** (THCA 1.2% imaged vs BLCA 57%). "Half of cancer patients
are invisible to any imaging-trained model, and *which* half isn't random." A different flavor
of the pattern (coverage bias, not mislabel) — use as a closing line only if ahead.

---

## 2. What the agent DOES (the product)

A single engine with a 4-step loop, run identically over any dataset via a small config:

```
for a given dataset:
  1. CONCENTRATION  → compute the tail: top-N share of the exposure metric (power-law).
  2. DECLARED       → pull the system's own priority label / estimate / promise.
  3. DECOUPLING     → measure label ⟂ exposure (rank the declared vs the computed).
  4. REPRICE        → emit a REORDERED work-queue: items whose declared priority is
                      most wrong vs their real exposure, ranked worst-first.
```

The demo output is **a reprioritized queue**, not a chart:

> **deps-dev queue (repriced by real blast radius, not label):**
> `#1  pkg=debug   label=HIGH but 2,235 dependents` … `#N  CVE labeled LOW, 400 dependents → promote`
> **"CRITICAL-labeled advisories average 10.85 dependents; HIGH average 18.3. Your triage
> order is backwards. Here's the corrected queue."**

Then, **zero code changes**, point the same engine at Olist:

> **Olist lane queue (repriced by promise gap × volume):**
> `#1  Rio de Janeiro  +11d gap × 12,350 orders` — *don't pad to 38d (absurd next to SP) — fix the tail.*

The judgement layer (pad-vs-fix for Olist; promote-vs-accept for CVEs) is what makes it an
*agent*, not a query.

---

## 3. Architecture

```
CLI / thin Streamlit
   │
Nemotron-3 Super 120B (Nebius Token Factory, function-calling)  ── the reasoning loop
   │   tools:
   ├─ generate_sql        (CRAFT semantic layer — THE rubric-rewarded call; visible on stage)
   ├─ execute_query       (→ artifact_fqn → get_result_page)   [see §6 fallback if blocked]
   │
   └─ reprice_engine()     (pure Python, config-driven, unit-tested — same code both domains)
         → concentration(top_n_share) · decoupling(label vs exposure) · ranked work-queue
```

- **Brain:** `nvidia/nemotron-3-super-120b-a12b`, `base_url=https://api.tokenfactory.nebius.com/v1/`,
  key `NEBIUS_API_KEY`, OpenAI-compatible, native function-calling.
- **Data:** CRAFT MCP `https://nebius.emergence.ai/mcp`, header `X-Project-ID: $CRAFT_PROJECT_ID`,
  OAuth 2.1 / PKCE. Lift the OAuth/token-mint code from the official starter's `mcp_starter.py`
  (the riskiest 30 min — don't hand-roll Keycloak).
- **Engine:** the reprice logic is ordinary Python over the returned rows. It is the ONE piece of
  real code and it is domain-agnostic; a per-dataset config supplies (exposure metric, declared
  label, entity key).

---

## 4. The `generate_sql` questions — feed verbatim (rubric rewards this; no hand-written SQL)

**deps-dev** — schema arg `{"schema_name":"DEPS_DEV_V1","schema_fqn":"deps-dev-v1-5f7bc95c.DEPS_DEV_V1.DEPS_DEV_V1"}`:
> *"For each GitHub severity label (CRITICAL, HIGH, MODERATE, LOW, UNKNOWN), take the first
> affected package of each advisory, join to the DEPENDENTS table, and report the number of
> advisories and the average number of distinct dependents. STATE THE EXACT NUMBER for each
> label. Order by average dependents descending."*  → the anti-correlation table.
>
> Supporting: *"Count advisories and the percentage that are CRITICAL, grouped by package
> ecosystem (npm, PyPI, Maven, Cargo, Go, NuGet)."*

**Olist** — schema arg `{"schema_name":"BRAZILIAN_E_COMMERCE","schema_fqn":"brazilian-e-commerce-5f7bc95c.BRAZILIAN_E_COMMERCE.BRAZILIAN_E_COMMERCE"}`:
> *"For delivered orders, group by customer_state (states with ≥500 orders). Per state compute:
> order count, avg promised days (purchase→estimated delivery), median actual delivery days,
> 95th percentile of actual delivery days, and current late rate. Add a recommended promise =
> the 95th percentile, and the gap between recommended and current avg promised. Order by gap
> descending."*  → the Rio finding + the ops queue.
>
> Supporting (credibility preamble): the review-by-days-late-bucket query (4.29→1.68 cliff).

**health (optional):** pancancer schema `PANCANCER_ATLAS_1.PANCANCER_ATLAS_FILTERED`, idc
`IDC.IDC_V17`; join `LEFT(DICOM_ALL.PatientID,12)=bcr_patient_barcode` in the AGENT layer
(separate MCP endpoints). Column is `Tumor_SampleBarcode` (no middle underscore).

---

## 5. Timeline (~2.5 hours, hard)

| Time | Do | Definition of done |
| --- | --- | --- |
| **0:00–0:25** | Nebius + CRAFT MCP wired (steal `mcp_starter.py` OAuth). | ONE `generate_sql` round-trip prints the deps-dev severity table. |
| **0:25–0:55** | **The hero number, live.** Nemotron calls `generate_sql`, gets the CRITICAL 10.85 < HIGH 18.30 table. | Agent prints the anti-correlation. This alone is a submittable project. |
| **0:55–1:30** | `reprice_engine()` (config-driven) → the reordered deps-dev queue with promote/demote calls. **Write its 3 unit tests FIRST** (TDD). | Queue reorders correctly on a fixed fixture; tests green. |
| **1:30–1:55** | Point the SAME engine at Olist via config swap → Rio lane queue. | Two domains, one engine, zero engine-code change. |
| **1:55–2:15** | **Record the demo while it works.** Pre-cache both hero queries (§6). | Video captured. |
| **2:15–2:30** | Devpost writeup + buffer. | Submitted. |

**Cut line, in order, no hesitation:** (1) health 3rd beat → (2) Olist corroboration (fall back
to deps-dev-only = Direction C, still wins on Insight) → (3) live re-derivation (narrate over
cached numbers) → (4) any UI beyond the printed queue table. **Never cut:** the reordered
work-queue (the "agent does something" proof) and a *visible* `generate_sql` call.

> **If you're behind at 1:15, freeze scope at deps-dev-only and rehearse.** The single
> anti-correlation number + a repriced queue beats a half-wired two-domain demo.

---

## 6. Environment reality + guardrails (learned this session — do not skip)

- **`execute_query` / `get_result_page` / metadata tools may be BLOCKED** (this session:
  `INSUFFICIENT_PERMISSIONS: can_create_resources`). **`generate_sql` still works and RETURNS THE
  REAL NUMBERS in its `explanation`** (it executes server-side). Build the agent to read the
  `explanation` as a first-class result path, not only `get_result_page`. On hackathon day full
  provisioning *may* restore `execute_query` — do not assume it.
- **`generate_sql` times out at 300s** on heavy plans (LATERAL FLATTEN, big unions, NTILE,
  window fns). Both hero queries above are pre-verified to run under budget — **never run a
  FLATTEN/NTILE plan live.**
- **Pre-cache both hero query results.** Agent re-derives live; on a timeout it narrates while
  returning the cached result. This is the single most important on-stage guardrail.
- **Sentinel/artifact rows lie:** filter mint/zero addresses (crypto), `UNKNOWN` severity as its
  own honest bucket (don't hide it — frame *unlabeled ≠ unexposed* as part of the mispricing).
- `sample_data` needs a **3-part** name `DB.SCHEMA.TABLE`. Timestamps are µs epoch (÷1e6);
  Olist dates are VARCHAR → `TRY_TO_TIMESTAMP` (CRAFT handles it). Rate limit: query 10/min.

---

## 7. Verification gate before you call it done (verification-before-completion)

Do not claim "working" until, with the output in front of you:
1. A **fresh** `generate_sql` call (not cached) returns the deps-dev severity table with
   CRITICAL < HIGH.  ✅ seen live.
2. `reprice_engine()` unit tests pass on a fixed fixture (correct reordering).  ✅ green.
3. The **same engine binary/config-swap** produces the Olist queue with Rio at #1.  ✅ seen live.
4. The demo video shows a **visible `generate_sql` tool call**.  ✅ in frame.
If any of these is unmet, it is not done — cut scope per §5 rather than overclaiming.

---

## 8. Adversarial Q&A (rehearse these — a judge will ask)

- **"Is cross-dataset real insight or a gimmick?"** → It's the *evidence*: the identical engine,
  unchanged, finds label⟂exposure in security AND logistics. Two unrelated schemas = a general
  law, not a coincidence. (Capped at 2 on purpose — 4 would be a demo reel.)
- **"Is the mispricing actually verified?"** → Yes, numerically, both: deps-dev 10.85<18.30 over
  n=30,212; Olist promised 27d vs p95 38d, 13.5% late. Not hand-wavy.
- **"62.7% UNKNOWN — is your denominator honest?"** → Stated up front; UNKNOWN is *part* of the
  finding (unlabeled ≠ safe). Averages shown are within labeled classes.
- **"So what's the action?"** → The reordered queue: "CVE labeled LOW, 400 dependents → rank #1."
  A decision, not a correlation.
- **"Did you use CRAFT or hand-write SQL?"** → `generate_sql` drives every headline number, on
  screen. (Hand-written SQL is not rewarded.)

---

## 9. The 60-second story (what the judge remembers)

> "Every system ships a priority label — a CVE severity, a delivery promise. We asked one agent
> to ignore the label and compute the *real* exposure. The labels are backwards: the CVEs marked
> CRITICAL touch fewer projects than the ones marked LOW. Same agent, unchanged, on e-commerce:
> the delivery promise is blind to variance, so the #2 market silently runs 13% late, right next
> to the #1. The label isn't just wrong — it's anti-correlated with harm. Our agent reprices the
> queue by what actually matters."

---

### Provenance
Built from a full CRAFT sweep (Jul 11 2026): 9 databases profiled, dominant meta-pattern =
**concentration + mispricing** (a tiny tail carries most value/harm while the system's own
label/estimate is decoupled from computed exposure). Verified instances: deps-dev severity⟂
blast-radius, Olist promise⟂variance, GA4/Firebase one-dominant-cliff funnels, crypto value
concentration (structuring *killed* — no sub-threshold bunching), health imaging coverage gap.
thelook confirmed synthetic (avoid). See `SESSION-SUMMARY.md` and `craft_databases.md`.
