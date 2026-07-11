# Luma: Emergence x Nebius Hack

**URL:** https://luma.com/f5smb6kp?tk=MMAqbM

**Status:** captured (pasted from the event page — WebFetch is blocked by Luma with HTTP 403).

---

## Theme

> **You don't query data. You investigate it.**

Spend one day in NYC building agentic data-intelligence applications on Emergence AI's CRAFT platform, powered by Nebius Token Factory GPU inference. Morning workshops to get you flying, an afternoon of open building, room judging over dinner, finalist demos on the main stage, and winners announced by 7pm.

Most data problems die in the plumbing: schema navigation, business-term resolution, gnarly SQL. CRAFT handles all of that for you over MCP — you ask questions in plain English, it generates accurate SQL against real enterprise databases, runs it, and hands you results and charts. So your day isn't about writing queries. It's about the interesting part: forming a hypothesis, interrogating the data, and delivering an insight someone would actually act on.

Bring any agent framework you like. Organizers will help connect it to CRAFT's MCP endpoint and point it at Nebius for inference.

## Schedule

Morning workshops → afternoon open building → room judging over dinner → finalist demos on the main stage → winners announced by 7pm.

## What makes this special

- **CRAFT handles the what, you build the why.** Accurate data retrieval from complex enterprise systems is solved for you — so you focus on investigating real business problems.
- **Real enterprise data.** You'll work against databases from the Spider 2.0 benchmark — the same real-world, enterprise-scale schemas that make most text-to-SQL systems fall over.
- **The before/after moment:** paste a nested GA4 schema into a generic assistant and ask for "top pages by engagement time" → broken SQL. Ask CRAFT → correct `LATERAL FLATTEN`. That's the value prop, live.
- **Serious inference.** Nebius Token Factory serves Nemotron-3 Super 120B (12B active, 1M context, native function calling) — a top open model for agentic tool use.
- **Bring-your-own-agent, MCP-native.** Use your favorite framework; connect in minutes.
- **Judged by the people building the frontier** — Emergence AI's founders and engineers, plus guests from the data/AI world.

## The challenges

One mission — use CRAFT to investigate a hypothesis in real enterprise data and produce an actionable finding — across five domains. Pick one, or bring your own hypothesis against any provided database.

| Challenge | What you'll investigate | Level |
| --- | --- | --- |
| E-commerce | Diagnose a revenue or conversion anomaly across orders, customers, and catalog | Beginner → Intermediate |
| Crypto / blockchain | A compliance team suspects a wallet cluster is structuring cross-chain transfers to dodge detection thresholds — find the pattern | Intermediate → Advanced |
| Biotech / clinical | Test whether imaging modalities correlate with molecular subtypes across cancers; produce publication-quality analysis (no genomics expertise required) | Intermediate → Advanced |
| Digital analytics | Find where the onboarding funnel loses mobile users vs. web — deeply nested schemas, the hardest SQL pattern in Spider 2.0 | Advanced |
| Dev infrastructure | Investigate reliability, usage, or cost patterns in engineering/ops data | Intermediate |

See [`craft_databases.md`](craft_databases.md) for what is actually inside each of the nine databases behind these challenges.

## Tech you'll use

- **CRAFT MCP endpoint** — a small, powerful tool loop: `list_databases` → `get_schema` → `generate_sql` → `execute_query` → `generate_plotly_chart`, plus DX helpers (`search_schema`, `explain_error`, `get_hint`). Connect via `craft-sdk` or a direct MCP config — one URL, one API key.
- **Nebius Token Factory** — OpenAI-compatible endpoint serving Nemotron-3 Super 120B. Point your agent at it in a few lines.

## How you'll be judged

An investigation showcase, not a query competition. Two rounds: first-round judging in breakout rooms (5-min demo + 5-min Q&A), then the top finalists present on the main stage.

- **CRAFT usage depth (30%)** — did you use the semantic layer (`generate_sql`, DX tools), or just raw queries?
- **Insight quality (30%)** — is the business finding actionable? Would a real analyst care?
- **Agent architecture (20%)** — is the design interesting? Multi-step reasoning, delegation, error recovery?
- **Story clarity (20%)** — can we follow what the agent did and why?
