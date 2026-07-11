# Project Ideas — Emergence × Nebius (CRAFT)

Every number in this file was **verified by querying the data through the CRAFT MCP**. Several
claims in the hackathon guide and in `craft_databases.md` turned out to be false — see
Landmines. Where an idea died on contact with the data, it's recorded as dead, so nobody
re-derives it.

**The only hard requirement: build on at least one database.** No mandatory track, no forced
tech. So the design goal is purely to maximise the rubric:

**CRAFT usage depth 30% · Insight quality 30% · Agent architecture 20% · Story clarity 20%**

Two things follow:

- **60% of the score is insight + CRAFT depth.** Pick the dataset with a *real finding* in it.
- **There is no uncrowded dataset.** Every pairing ships with a suggested project printed next
  to it in the guide ("churn agent", "blast-radius investigation", …). Uniqueness has to come
  from **the question, not the data.** Pick a lane, then deliberately ask the question that
  *isn't* the one printed beside it.

---

# 🏆 THE PROJECT: "The Padding Paradox" (`brazilian-e-commerce`)

> **Olist is padding delivery promises across all ~99,000 orders to hide the failures of
> 30 sellers.**

That's the finding. It is counterintuitive, fully supported by the data, and the action is
unmissable. Below is the investigation, beat by beat — every number verified.

## Beat 1 — Kill the obvious hypothesis

The guide's canonical prompt for the ecommerce pairing is *"a customer-insights agent
investigating churn hypotheses."* So test churn first, honestly:

| Metric | Value |
| --- | --- |
| Distinct customers (`customer_unique_id`) | 96,096 |
| Customers who ever ordered twice | 2,997 |
| **Repeat rate** | **3.12%** |

And repeat rate **by the review score of their first order**:

| First-order review | Repeat rate |
| --- | --- |
| ⭐ 1 star | **3.26%** |
| ⭐⭐⭐⭐⭐ 5 stars | **3.17%** |

**A ruined delivery has zero effect on whether a customer comes back.** There is no churn to
analyse — nobody comes back regardless. The canonical prompt is a **dead end**, and most teams
following it will present noise or quietly fabricate a narrative.

*(The other half of that pairing, `thelook`, is synthetic and has no signal either — see
Landmines. So the printed prompt for this lane is a trap on both sides.)*

## Beat 2 — So what is the actual asset? Reviews.

Retention isn't the lever. On a **marketplace**, the review score is the trust and ranking
currency. And late delivery annihilates it:

| Delivery vs. promise | Orders | Avg review | % 1-star |
| --- | --- | --- | --- |
| Early | 88,653 | 4.29 | 6.6% |
| On time | 1,291 | 4.03 | 8.5% |
| 1–3 days late | 1,856 | 3.29 | 25% |
| 4–7 days late | 1,756 | 2.10 | 58.5% |
| 8–15 days late | 1,609 | 1.68 | **70%** |

Clean, monotonic, brutal. (This much is also what the reference "Seller Delivery Intelligence
Agent" found — so **do not stop here.** This is the setup, not the punchline.)

## Beat 3 — The damage is brutally concentrated

Of 2,970 sellers and 8,714 late items:

| Sellers | Count | Share of ALL late items |
| --- | --- | --- |
| **Top 1%** | **30** | **29.63%** |
| Top 5% | 149 | 57.82% |
| Top 10% | 297 | 72.72% |
| Top 20% | 594 | 86.92% |

**Thirty sellers cause nearly a third of all late deliveries.**

## Beat 4 — The punchline

Look again at Beat 2: **88,653 orders arrive early, only 1,291 on time.** Olist inflates its
delivery estimate on essentially *every* order — a marketplace-wide penalty, a slower promise
shown to every customer of every honest seller — in order to absorb the failures of **1% of
its sellers**.

**The padding is a global anaesthetic for a local infection.**

### The action

1. **Triage the 30.** Fix, re-route, or delist them → recovers ~30% of all late deliveries,
   and with them the 1-star reviews that late deliveries generate at a 58–70% rate.
2. **Then tighten the promise for the other 2,940 sellers** — who are currently being made to
   look slow to cover for sellers they've never met.

## ⚠️ The one claim you must NOT make

**Do not say "tighter promises will lift conversion."** Olist has **no clickstream** — no
sessions, no browsing, no cart events. Conversion lift is an industry belief you *cannot
measure in this data*, and a judge can puncture it in one question.

Say only what the data supports: **you can tighten promises without increasing late-delivery
risk.** The argument stays bulletproof.

## Agent architecture — the falsification loop

This is where the 20% architecture score lives. The agent doesn't run a report; it runs an
**investigation** and is willing to be wrong:

```
hypothesise  →  test  →  FALSIFY  →  re-hypothesise  →  localise  →  recommend
   churn         3.12%    flat by      reviews are      Pareto:      triage 30,
   drives        repeat   review        the real         30 sellers   then tighten
   the loss      rate     score         asset            = 30%        the promise
```

An agent that **kills its own hypothesis with evidence** and pivots is exactly the multi-step
reasoning the rubric asks for — and almost nobody will demo it. Devpost literally calls this
an *"investigation showcase, not a query competition."* Lean all the way into that.

Use CRAFT's DX tools (`search_schema`, `explain_error`, `get_hint`) on the way through — that's
the 30% CRAFT-depth score, and it's cheap to earn.

## The voice layer (ElevenLabs — teammate has unlimited credits)

Voice earns **no points directly** — there is no UI/UX category, and it only touches the 20%
story slice. So it is strictly a *finishing* move, never a foundation.

But the demo writes itself, because the finding is a decision:

> **"Should we tighten our delivery promises?"**
> *"No. First, fire these thirty sellers."*

**Architecture — keep Nemotron as the brain:**

```
Mic / phone
   │
ElevenLabs  ── STT + TTS ONLY (ears and mouth)
   │
Your agent loop
   │
Nebius Token Factory — Nemotron-3 Super 120B  ← reasoning + function calling
   │
CRAFT MCP — generate_sql → execute_query → get_result_page
```

Don't let ElevenLabs' built-in LLM do the thinking. Nebius is *strategic, not mandatory* — the
judges are Emergence + Nebius engineers and the prizes are Nebius credits — but Nemotron has
native function calling and 1M context, so it should own the tool loop. (If you want
ElevenLabs Agents for turn-taking, run it in **custom-LLM mode** pointed at Nebius's
OpenAI-compatible endpoint.)

## Build sequence

1. **The investigation.** All four beats, reproducible through `generate_sql`. This is 60%.
2. **The falsification loop** as a real agent, with error recovery. This is 20%.
3. **Voice, time-boxed, last.** Text path stays working underneath.
4. **Record a backup demo video the moment voice works.** If the room's WiFi or mic betrays
   you, play the tape.

> **The rule:** if voice isn't working by your cutoff, ship without it and the project is still
> strong. If that's not true, the layering is wrong.

---

# Runner-up ideas

## 💡 Cohort Bias Auditor — "a datasheet for your cohort" (`idc`)

Best of the health ideas, and orthogonal to its lane's printed prompt (*"correlate imaging
modality with molecular subtype"*). Everyone there will correlate what's **in** the data; you'd
ask what **isn't**.

`IDC.TCGA_CLINICAL_REL9` holds all **11,353** TCGA patients with `race`, `ethnicity`, `gender`,
`age`, `stage`, `vital_status`. Mark a patient as *imaged* if their `case_barcode` appears as a
`PatientID` in `DICOM_ALL` — a single-connection join — and ask **who is missing.** Verified:

| Cancer | Imaged | Total | Rate |
| --- | --- | --- | --- |
| **LAML** (leukemia) | **0** | 200 | **0.0%** |
| SKCM (melanoma) | 151 | 470 | 32.1% |
| BRCA | 562 | 1,098 | 51.2% |
| **KIRC** (kidney) | 416 | 537 | **77.5%** |

A **77-point spread**. IDC is marketed as pan-cancer; it is actually a *solid-tumor* cohort with
a heavy kidney skew and **zero leukemia patients**.

Also verified, on race (all 11,353 patients): **Asian 40.15% vs White 44.95%** imaged — ~2.4σ,
**p≈0.016, significant.** But **Black 44.65% vs White 44.95% — no gap at all.** So "the imaging
cohort is racially biased" is *false as stated*; only the narrower Asian finding survives. Say
the narrow true thing.

**The trap, which is also the feature:** LAML is 0% because leukemia is a blood cancer you don't
CT-scan — that's **medicine, not bias**, and a sharp judge will say so instantly. So make the
agent *distinguish clinically-expected absence from genuine sampling bias*. That discrimination
**is** the project, and it's real multi-step reasoning.

- ❌ Dead end within this idea: **imaging rate by stage** — no signal (Stage I 50.7%, Stage IV
  53.9%, Stage IVA 35.4%). Noise. Don't dress it up.

## 💡 Blast Radius (`deps-dev` + `github-repos`) — ⚠️ NOT original

Dependency CVE blast radius is **literally the project printed next to this dataset pairing** in
the guide ("a supply-chain vulnerability blast-radius investigation"). Every team in that lane
lands here. Being the fifth-best blast radius is worse than being the only anything-else.

*If* you ever return to it, the only defensible angle is the reframe — **"47 vulns collapse into
3 upgrades"** as a minimum set-cover over the dependency graph (uniquely possible because
`DEPENDENTS.MinimumDepth` precomputes the transitive graph), plus the abandonment score:
**`once` has 941 dependent packages and was last published in September 2016.** Lead with those
and never say the words "blast radius."

## 💡 Crypto circular-flow detection — ⚠️ weak

Recursive CTE over 18.5M Ethereum token transfers to find A→B→C→A wash-trading loops. Gorgeous
graph. But it's a named challenge (crowded) and there is **no ground truth** — the demo reduces
to "these wallets look suspicious, trust me," which judges cannot verify. Insight quality
unverifiable.

---

# Landmines (all verified the hard way)

### Data traps

- **`thelook` is SYNTHETIC with no latent structure.** Return rate (11–12%) and net margin per
  customer (~$58) are *identical* across every acquisition channel. Any correlation you hunt for
  returns null. It's also the most crowded dataset. **Avoid entirely.**
- **Olist churn is unanalysable.** 3.12% repeat rate, flat across review scores. The canonical
  "churn agent" prompt for this lane is a dead end.
- **Olist has no clickstream.** No sessions, no browsing, no cart. Anything about *conversion*
  is unmeasurable here.
- **`deps-dev-v1` is NOT a time series of the dependency graph.** `ADVISORIES` and `DEPENDENTS`
  have exactly **one snapshot each** (`DEPENDENCIES` 19, `PACKAGEVERSIONS` 44). You cannot
  "watch a vulnerability spread." The real temporal signal is the event timestamps —
  `ADVISORIES.Disclosed` and `PACKAGEVERSIONS.UpstreamPublishedAt` — which is better anyway.
- **`github-repos` is a sample.** No issues/PRs tables. Only 80 `package.json` files across 76
  repos.

### Process traps

- **Don't let voice eat the investigation.** 60% of the score is insight + CRAFT depth; voice
  touches only the 20% story slice. Build it last, with a text fallback and a recorded backup.
- **Don't claim what the data can't support.** The fastest way to lose a judge is one
  unfalsifiable sentence in an otherwise rigorous demo.

### MCP gotchas

- **`sample_data` wants a 3-part name** (`DATABASE.SCHEMA.TABLE`), *not* the 4-part FQN the tool
  description advertises. The 4-part form returns `HTTP 400: got 4 parts`. Every *other* tool
  (`get_schema`, `search_schema`) does want the full FQN.
- **`execute_query` does not return rows.** It returns an `artifact_fqn`; call `get_result_page`
  with it to see the data.
- **All timestamps are microsecond epoch integers.** Divide by 1,000,000 before `TO_TIMESTAMP`.
- **`generate_sql` often answers the question in its `explanation`** before you even run the
  SQL — great for fast profiling.
