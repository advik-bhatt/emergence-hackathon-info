# Session summary — CRAFT dataset investigation (Jul 11, 2026)

What we did: probed **all nine CRAFT databases** through the MCP to find a hackathon project for
**Emergence × Nebius** that is *real, actionable, and not what everyone else will build*.

Everything here was **verified by querying live data**. Several claims in the hackathon guide —
and in our own earlier notes — turned out to be **false**. Those are recorded so nobody
re-derives them.

**Outcome → [`project-ideas.md`](./project-ideas.md): THE PROMISE ENGINE** (Olist / brazilian-e-commerce).

---

## 1. The headline finding

**Olist's delivery promise scales with *distance* but not with *reliability*.**

Rio de Janeiro is the proof:

| | Median actual | p95 actual | Promised | Late rate | Orders |
| --- | --- | --- | --- | --- | --- |
| **RJ** | **12 days** | **38 days** | 27 days | **13.5%** | 12,350 (#2 market) |
| SP | 7 days | 20 days | 19.8 days | 5.9% | 40,494 |

**Rio is not slow — it's unpredictable.** A 12-day median with a 38-day tail. Olist promises 27,
so it breaks its word to ~1 in 7 Rio customers, in its second-biggest market, right next door to
São Paulo. Distance explains Maranhão and Pará. **Distance cannot explain Rio.**

Meanwhile SP, MG and PR come back **already well-calibrated** (promise gap ≈ 0) — so the
estimator isn't stupid; it fails precisely where the tail is fat.

**The product:** an agent that (a) sets the delivery promise that actually hits a 95% on-time
target, and (b) ranks lanes by `promise gap × volume` into an ops work-queue — and decides per
lane whether to **pad the promise** or **fix the lane**.

---

## 2. Hypotheses we killed (this is most of the value)

Each of these looked plausible and is **false**. Two of them were our own confident mistakes,
caught by checking properly.

| Hypothesis | Verdict | Evidence |
| --- | --- | --- |
| "Bad delivery drives customers away" (**the guide's suggested prompt**) | ❌ **DEAD** | Repeat rate **3.12%** and *flat by review score*: 1-star first order → **3.26%** repeat; 5-star → **3.17%**. No churn signal exists. |
| "Late delivery destroys reviews" | ✅ **TRUE** | Avg review **4.29 → 1.68**; 1-star rate **6.6% → 70%** as delivery slips past promise. |
| "A few terrible sellers cause the lateness" | ❌ **DEAD** (our error) | **Volume artifact.** Top-30 sellers by late *count* are 9.39% late vs 7.41% baseline — barely worse. They're **big, not bad**. Ranked by *rate* (≥50 items): **not one seller is above 40% late**; half of all late items come from the ordinary 5–10% bucket. Lateness is **diffuse**. |
| "The promise is a dumb flat buffer" | ❌ **DEAD** (our error) | It **is** distance-adjusted: SP ~20d promised, PA ~38d. |
| "It's adjusted for distance but not **variance**" | 🏆 **SURVIVES** | Slack barely moves (9.6→14.4d) while late rate moves 4× (5%→20%). Riskiest lanes get the *least* buffer. |

> The "30 bad sellers" mistake matters: the original recommendation was **"fire your 30 worst
> sellers,"** which would have meant firing the **biggest** sellers. Caught before it shipped.

---

## 3. Dataset landmines (verified — saves hours)

- **`thelook-ecommerce` is SYNTHETIC and has no latent structure.** Return rate (11–12%) and net
  margin per customer (~$58) are *identical* across every acquisition channel. Any correlation
  you hunt for **returns null**. It's also the most crowded dataset (the reference agent used it).
  **Avoid entirely.**
- **Olist has no clickstream.** No sessions, no page views, no cart. Anything about *conversion*
  is **unmeasurable** — never claim "a tighter promise lifts conversion."
- **`deps-dev-v1` is NOT a time series of the dependency graph.** `ADVISORIES` and `DEPENDENTS`
  have **one snapshot each** (`DEPENDENCIES` 19, `PACKAGEVERSIONS` 44). You cannot "watch a
  vulnerability spread." The real temporal signal is event timestamps (`Disclosed`,
  `UpstreamPublishedAt`).
- **"Blast radius" on `deps-dev` + `github-repos` has zero originality** — it is *literally the
  project printed next to that dataset pairing* in the guide.
- **`github-repos` is a sample.** No issues/PRs. Only 80 `package.json` across 76 repos.
- **`crypto`** — viable (18.5M Ethereum token transfers, 2016–2024) but it's a named challenge
  and fraud findings have **no ground truth**; the demo reduces to "trust me."

### The strategic lesson
**There is no uncrowded dataset.** Every pairing ships with a suggested project printed beside it
("churn agent", "blast-radius investigation", …). **Uniqueness must come from the question, not
the data.** Pick a lane, then deliberately ask the question that *isn't* the printed one.

---

## 4. The health idea (runner-up, verified)

**Cohort Bias Auditor** (`idc`). Mark a TCGA patient as *imaged* if their `case_barcode` appears
as a `PatientID` in `DICOM_ALL` — a single-connection join on `TCGA_CLINICAL_REL9` (11,353
patients) — then ask **who is missing**.

- Imaging rate runs **0% (LAML, leukemia) → 77.5% (KIRC, kidney)**. A 77-point spread. IDC is
  marketed as pan-cancer; it is a **solid-tumor cohort with zero leukemia patients**.
- Race (all 11,353): **Asian 40.15% vs White 44.95%** — ~2.4σ, **p≈0.016, real.** But
  **Black 44.65% vs White 44.95% — no gap.** So "the imaging cohort is racially biased" is
  **false as stated**; only the narrow Asian finding survives.
- **The trap that's also the feature:** LAML's 0% is **medicine, not bias** (you don't CT-scan a
  blood cancer). The agent must *distinguish clinically-expected absence from sampling bias* —
  that discrimination **is** the project.
- ❌ Dead within this idea: imaging rate **by stage** — no signal (Stage I 50.7%, Stage IV 53.9%).

---

## 5. CRAFT MCP gotchas

- **`execute_query` does NOT return rows.** It returns an `artifact_fqn` → call
  `get_result_page` with it.
- **`sample_data` wants a 3-part name** (`DATABASE.SCHEMA.TABLE`) — *not* the 4-part FQN the tool
  docs advertise (that returns `HTTP 400: got 4 parts`). Every other tool wants the full FQN.
- **All timestamps are microsecond epoch integers** — divide by 1,000,000 before `TO_TIMESTAMP`.
  Olist's dates are **VARCHAR** → `TRY_TO_TIMESTAMP`.
- **`generate_sql` often answers the question in its `explanation`** before you even run the SQL —
  great for fast profiling.
- Nebius Token Factory is an **OpenAI-compatible endpoint** — just change `base_url`.

---

## 6. Decisions made

- **Dataset: Olist** (`brazilian-e-commerce`) — the *real* half of the ecommerce pairing.
- **Voice (ElevenLabs) CUT** — ~2 hours left. There is **no UI/UX category** in the rubric; voice
  touches only the 20% story slice while **60% is insight + CRAFT depth**.
- **Blast Radius dropped** — unoriginal (it's the printed prompt for that pairing).
- **The "Falsifier" framing dropped** — an agent that only kills hypotheses has no actionable
  output. The falsification work is kept as the *credibility preamble* to a real product, not as
  the product itself.

Rubric being optimised: **CRAFT depth 30% · Insight quality 30% · Agent architecture 20% ·
Story clarity 20%.** Only hard requirement: build on ≥1 database.
