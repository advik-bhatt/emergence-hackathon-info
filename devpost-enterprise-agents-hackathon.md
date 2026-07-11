# Devpost: Enterprise Agents Hackathon (Emergence x Nebius)

**URL:** https://devpost.com/software/1324730/joins/nIJRd1dC-_fWlac8dwWRVA
**Deadline:** Jul 11, 2026 @ 5:00pm EDT (submission day-of, in-person, NYC)
**Visibility:** Public, 9 participants at time of capture
**Prizes:** 4 non-cash prizes

This is the real Emergence x Nebius hackathon page (the earlier `luma-emergence-x-nebius.md`
stub in this repo is still unfetched — Luma keeps 403ing automated fetches; this Devpost page
is the authoritative source for now).

## Overview

A day to build the next generation of enterprise-grade AI agents — hands-on workshops, a full
day to build, judging from Emergence and Nebius engineers.

> You don't query data. You investigate it.

Spend one day in NYC building agentic data-intelligence applications on Emergence AI's **CRAFT**
platform, powered by **Nebius Token Factory** GPU inference. Morning workshops, an afternoon of
open building, room judging over dinner, finalist demos on the main stage, winners announced by
7pm.

Most data problems die in the plumbing: schema navigation, business-term resolution, gnarly SQL.
CRAFT handles that over MCP — ask questions in plain English, it generates accurate SQL against
real enterprise databases, runs it, hands back results and charts. The day is about forming a
hypothesis, interrogating the data, and delivering an insight someone would actually act on.

Bring any agent framework; they'll help connect it to CRAFT's MCP endpoint and point it at
Nebius for inference.

## What makes this special

- **CRAFT handles the what, you build the why.** Accurate data retrieval from complex enterprise
  systems is solved for you — focus on investigating real business problems.
- **Real enterprise data.** Databases from the **Spider 2.0 benchmark** — real-world,
  enterprise-scale schemas that break most text-to-SQL systems.
- The before/after moment: paste a nested GA4 schema into a generic assistant and ask for "top
  pages by engagement time" → broken SQL. Ask CRAFT → correct `LATERAL FLATTEN`.
- **Serious inference.** Nebius Token Factory serves **Nemotron-3 Super 120B** (12B active, 1M
  context, native function calling) — a top open model for agentic tool use.
- **Bring-your-own-agent, MCP-native.** Use your favorite framework; connect in minutes.
- Judged by Emergence AI's founders/engineers plus guests from the data/AI world.

## The challenges (pick one, or bring your own hypothesis)

| What you'll investigate | Level | Domain |
|---|---|---|
| Diagnose a revenue or conversion anomaly across orders, customers, and catalog | Beginner → Intermediate | E-commerce |
| A compliance team suspects a wallet cluster is structuring cross-chain transfers to dodge detection thresholds — find the pattern | Intermediate → Advanced | Crypto / blockchain |
| Test whether imaging modalities correlate with molecular subtypes across cancers; publication-quality analysis (no genomics expertise needed) | Intermediate → Advanced | Biotech / clinical |
| Find where the onboarding funnel loses mobile users vs. web — deeply nested schemas, the hardest SQL pattern in Spider 2.0 | Advanced | Digital analytics |
| Investigate reliability, usage, or cost patterns in engineering/ops data | Intermediate | Dev infrastructure |

## Tech you'll use

- **CRAFT MCP endpoint** — tool loop: `list_databases` → `get_schema` → `generate_sql` →
  `execute_query` → `generate_plotly_chart`, plus DX helpers `search_schema`, `explain_error`,
  `get_hint`. Connect via `craft-sdk` or direct MCP config — one URL, one API key.
- **Nebius Token Factory** — OpenAI-compatible endpoint serving Nemotron-3 Super 120B. Point your
  agent at it in a few lines.

## How you're judged

Investigation showcase, not a query competition. Two rounds: first-round judging in breakout
rooms (5-min demo + 5-min Q&A), then top finalists present on the main stage.

- **CRAFT usage depth — 30%** — did you use the semantic layer (`generate_sql`, DX tools), or
  just raw queries?
- **Insight quality — 30%** — is the business finding actionable? Would a real analyst care?
- **Agent architecture — 20%** — is the design interesting? Multi-step reasoning, delegation,
  error recovery?
- **Story clarity — 20%** — can we follow what the agent did and why?

## Sponsors

- Nebius
- Emergence

## Prizes (4 non-cash)

- **First Prize** (1 winner) — 6-month CRAFT access + $5,000 Nebius Credits
- **2nd Place** (1 winner) — CRAFT access + Nebius Token Factory credits
- **3rd Place** (1 winner) — CRAFT access + Nebius Token Factory credits
- **Per-challenge standouts** (1 winner) — CRAFT access + Nebius Token Factory credits

## Judges

- Colin Lowenberg — Dev Advocate, Nebius
- Vishnu Mohan — Product Lead, Emergence
- Sharad — CPO, Emergence
- Abhishek — Lead Engineer, Emergence
- Bhaskar — Engineering Manager, Emergence

## To-dos from the page

- Sign up for the Emergence Discord
- Sign up for the Nebius Builder Program

## Eligibility

Above legal age of majority in country of residence; all countries/territories excluding
standard exceptions.
