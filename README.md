# Enterprise Agents Hackathon

Organizer/sponsor research and setup info for the **Enterprise Agents Hackathon**
(Devpost, hosted by Emergence, judged by Emergence + Nebius engineers).

- Devpost: https://ai-healthcare-hack.devpost.com/ (URL slug is misleading — this is the Emergence/Nebius Enterprise Agents Hackathon, NOT a healthcare hack)
- Location: NYC, in-person, one day
- Deadline: **Jul 11, 2026 @ 5:00pm EDT**
- Luma (RSVP/signup): https://luma.com/f5smb6kp?tk=MMAqbM
- NDA form: https://scanned.page/6tITpm
- Hackathon homepage: https://www.emergence.ai/hackathon#start
- Devpost project/submission page: https://devpost.com/software/1324730/joins/nIJRd1dC-_fWlac8dwWRVA
- Reference repo (organizer-provided starter): https://github.com/EmergenceAI/nebius-emergence-hackathon
- Reference repo (Claude/Codex ↔ Nebius proxy): https://github.com/opencolin/claude-codex-nebius-proxy
- To-dos: sign up for Emergence Discord, sign up for Nebius Builder Program
- Questions: email the hackathon manager (via Devpost page)

## Theme

"You don't query data. You investigate it." Build agentic data-intelligence
applications on **Emergence AI's CRAFT platform**, powered by **Nebius Token
Factory** GPU inference. CRAFT handles schema navigation, business-term
resolution, and SQL generation over MCP so the day is spent on hypothesis
formation and delivering an actionable insight, not writing queries.

Format: morning workshops → afternoon open building → room judging over
dinner → finalist demos on main stage → winners announced by 7pm.

## Sponsors

- **Emergence** — CRAFT platform (agentic data-intelligence over MCP)
- **Nebius** — Token Factory GPU inference (OpenAI-compatible endpoint)

## Tech you'll use

- **CRAFT MCP endpoint** — tool loop: `list_databases` → `get_schema` →
  `generate_sql` → `execute_query` → `generate_plotly_chart`, plus DX helpers
  `search_schema`, `explain_error`, `get_hint`. Connect via `craft-sdk` or a
  direct MCP config — one URL, one API key.
- **Nebius Token Factory** — OpenAI-compatible endpoint serving
  **Nemotron-3 Super 120B** (12B active params, 1M context, native function
  calling), a top open model for agentic tool use.
- Bring your own agent framework — organizers help connect it to CRAFT's MCP
  endpoint and point it at Nebius for inference.
- Data: real enterprise-scale databases from the **Spider 2.0 benchmark**
  (the same schemas that break most text-to-SQL systems).

## The challenges (pick one, or bring your own hypothesis against any provided DB)

| Domain | What you'll investigate | Level |
|---|---|---|
| E-commerce | Diagnose a revenue or conversion anomaly across orders, customers, and catalog | Beginner → Intermediate |
| Crypto / blockchain | A compliance team suspects a wallet cluster is structuring cross-chain transfers to dodge detection thresholds — find the pattern | Intermediate → Advanced |
| Biotech / clinical | Test whether imaging modalities correlate with molecular subtypes across cancers; produce publication-quality analysis (no genomics expertise required) | Intermediate → Advanced |
| Digital analytics | Find where the onboarding funnel loses mobile users vs. web — deeply nested schemas, the hardest SQL pattern in Spider 2.0 | Advanced |
| Dev infrastructure | Investigate reliability, usage, or cost patterns in engineering/ops data | Intermediate |

## Judging

Two rounds: first-round breakout-room judging (5-min demo + 5-min Q&A), then
top finalists present on the main stage.

- **CRAFT usage depth (30%)** — did you use the semantic layer
  (`generate_sql`, DX tools), or just raw queries?
- **Insight quality (30%)** — is the business finding actionable? Would a
  real analyst care?
- **Agent architecture (20%)** — is the design interesting? Multi-step
  reasoning, delegation, error recovery?
- **Story clarity (20%)** — can we follow what the agent did and why?

Judges: Colin Lowenberg (Dev Advocate, Nebius), Vishnu Mohan (Product Lead,
Emergence), Sharad (CPO, Emergence), Abhishek (Lead Engineer, Emergence),
Bhaskar (Engineering Manager, Emergence).

## Prizes (4 non-cash)

- **1st place**: 6-month CRAFT access + $5,000 Nebius Credits
- **2nd place**: CRAFT access + Nebius Token Factory credits
- **3rd place**: CRAFT access + Nebius Token Factory credits
- **Per-challenge standout** (1 winner): CRAFT access + Nebius Token Factory credits

## Related repo (out of scope, noted for context)

The same Devpost account also has a listing for **AI Healthcare Hack NYC**
(Arya Health + Twilio AI Startup Searchlight, deadline Jul 11 2026 @ 3:30pm
EDT, must use Twilio for telephony to qualify for prizes). That is a
**separate, unrelated hackathon** — not tracked in this repo. Flag to
@advik-bhatt if both are being entered simultaneously.
