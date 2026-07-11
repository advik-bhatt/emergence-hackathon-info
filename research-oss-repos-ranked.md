# Open-source repo research — Enterprise Agents Hackathon (Emergence x Nebius)

*Compiled 2026-07-11, ~4h before the 5pm EDT deadline. All facts below were adversarially verified against live repo pages and source files, not just READMEs.*

## 1. Method

Starting from the sponsor requirements (Emergence CRAFT via MCP as the text-to-SQL/charting layer; Nebius Token Factory serving Nemotron-3 Super 120B over an OpenAI-compatible API) and the judging rubric (CRAFT depth 30%, insight quality 30%, architecture 20%, story 20%), we searched for high-star open-source agent frameworks and data-analysis agents that (a) consume remote MCP servers natively and (b) run on any OpenAI-compatible endpoint. Each candidate was verified at source level (stars, license, activity, the exact config/class where `base_url` and MCP headers plug in), then scored on integration effort against the 4h window and rubric fit, with a concrete swap-point plan for CRAFT and Nebius.

49 raw candidates → 47 unique after dedup → top 16 verified adversarially → 13 survivors.

## 2. Ranked shortlist

| # | Repo | Stars | Pedigree | Current stack | Sponsor gap | Effort (h) | Verdict |
|---|------|-------|----------|---------------|-------------|-----------|---------|
| 1 | [lastmile-ai/mcp-agent](https://github.com/lastmile-ai/mcp-agent) | 8.4k | LastMile AI; canonical MCP-native impl of Anthropic's agent patterns | Python; MCPApp + AugmentedLLM; YAML-configured MCP servers | None — CRAFT = 1 YAML block, Nebius = 2 YAML lines | 2.5 | **top-pick** (fit 9/10) |
| 2 | [evalstate/fast-agent](https://github.com/evalstate/fast-agent) | 3.9k | Most MCP-spec-complete client; daily releases (v0.9.5 Jul 10) | Python decorators; chain/parallel/evaluator-optimizer workflows | None — native MCP OAuth2.1/PKCE + generic OpenAI provider | 2.5 | **top-pick** (fit 8.5/10) |
| 3 | [langchain-ai/deepagents](https://github.com/langchain-ai/deepagents) | 26.1k | Official LangChain; Nebius's own blueprint pairs it with Nemotron | LangGraph harness: planning, sub-agents, virtual FS | MCP via langchain-mcp-adapters; Nebius = ChatOpenAI base_url | 3 | **top-pick** (fit 8.5/10) |
| 4 | [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | 27.8k | Official OpenAI SDK; v0.18.2 released today | Agents/handoffs/guardrails; MCPServerStreamableHttp | Nebius = AsyncOpenAI base_url; must disable OpenAI tracing | 2.5 | **top-pick** (fit 8.5/10) |
| 5 | [huggingface/smolagents](https://github.com/huggingface/smolagents) | 28.3k | Official Hugging Face; v1.26.0 | CodeAgent (LLM writes Python actions); MCPClient streamable-http | Nebius = OpenAIModel(api_base=...); no OAuth client | 2 | **top-pick** (fit 8/10) |
| 6 | [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | 18.4k | Official Pydantic team; v2.9.0 today | Typed Agent + MCPToolset (bearer/oauth auth); pydantic-graph | None — has a built-in NebiusProvider | 2.5 | **top-pick** (fit 8/10) |
| 7 | [langchain-ai/langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) | 3.6k | Official LangChain org; v0.3.0 Jun 2026 | Bridge lib: MultiServerMCPClient → LangChain tools | None; PKCE may need starter's token code | 1.5 | **top-pick (as glue)** (fit 8/10) |
| 8 | [mcp-use/mcp-use](https://github.com/mcp-use/mcp-use) | 10.3k | Top-starred MCP client lib; v1.34.3 Jul 8 | MCPClient + MCPAgent over any LangChain LLM | None — verified headers/auth in HttpConnector | 2 | viable (fit 7/10) |
| 9 | [ruc-datalab/DeepAnalyze](https://github.com/ruc-datalab/DeepAnalyze) | 4.3k | Renmin Univ. DataLab; fine-tuned DeepAnalyze-8B | Tag-protocol loop, Docker sandbox | Not MCP-native; CRAFT must be shoehorned into codegen sandbox | 4.5 | stretch (fit 6.5/10) |
| 10 | [crazycloud/data-analysis-llm-agent](https://github.com/crazycloud/data-analysis-llm-agent) | 83 | Small; stale since May 2024 | Chainlit + AsyncOpenAI loop, SQLite/Postgres, inline Plotly | No MCP/OAuth plumbing at all | 3 | viable — UI quarry (fit 6.5/10) |
| 11 | [nebius/token-factory-cookbook](https://github.com/nebius/token-factory-cookbook) | 111 | Official Nebius org; pushed Jul 1 2026 | Linear LangGraph SQL pipeline + Streamlit; ChatNebius | CRAFT replaces 5 of its 7 modules; no MCP client | 4 | stretch — prompt quarry (fit 4/10) |
| 12 | [sqlchat/sqlchat](https://github.com/sqlchat/sqlchat) | 5.8k | Bytebase team; trickle-maintained Next.js 13 | Single-shot completion proxy, own DB connectors | No agent loop, no tool calling, no chart rendering path | 6 | stretch (fit 4/10) |
| 13 | [sinaptik-ai/pandas-ai](https://github.com/sinaptik-ai/pandas-ai) | 23.6k | Sinaptik AI; v3.0.0 | Generate-then-execute code-gen pipeline via LiteLLM | CRAFT *collides* with its core; zero MCP support | 7 | stretch (fit 4/10) |

Notable rejection: **vanna-ai/vanna** (23.8k stars) — **archived Mar 29, 2026** (read-only). Do not use; useful as a story hook ("biggest OSS text-to-SQL just went closed, CRAFT is the open replacement").

## 3. Top 3 deep dives

### 3.1 lastmile-ai/mcp-agent — judging fit 9/10, ~2.5h

**What it is.** The canonical MCP-native framework implementing Anthropic's "Building Effective Agents" patterns as composable workflows: Orchestrator-Workers, Evaluator-Optimizer, Router, Parallel, Swarm, Deep Research. Agents declare `server_names` binding them to MCP servers in `mcp_agent.config.yaml`; an `AugmentedLLM` runs the tool loop. Apache-2.0, 8.4k stars, commits through Jan 2026.

**Why it fits the rubric.** It converts the rubric into framework features. Evaluator-Optimizer mechanically forces additional `generate_sql → execute_query → explain_error/get_hint` cycles until a critic approves — that is "CRAFT usage depth" (30%) as a first-class construct, and the critic gate raises insight quality (30%). Orchestrator-Workers is the reference architecture judges recognize (20%), and "we composed Anthropic's agent patterns over CRAFT on Nebius" is a one-sentence story (20%).

**Integration plan:**
1. `uv add mcp-agent` and scaffold `mcp_agent.config.yaml` + `mcp_agent.secrets.yaml`.
2. **CRAFT in:** add one block under `mcp.servers`:
   ```yaml
   craft:
     transport: streamable_http
     url: <CRAFT MCP URL>
     headers:
       Authorization: "Bearer <key>"
   ```
   If the event enforces Keycloak OAuth2.1/PKCE, use `auth.oauth` via `MCPOAuthClientSettings` — both modes verified in `src/mcp_agent/config.py`. All eight CRAFT tools auto-discover on any agent with `server_names=["craft"]`. Nothing in CRAFT is replaced.
3. **Nebius in:** set `openai: {base_url: <Token Factory endpoint>, default_model: <Nemotron-3 Super 120B id>}` in config, Nebius key as `openai.api_key` in secrets (or env `OPENAI_BASE_URL` / `OPENAI_API_KEY` / `OPENAI_DEFAULT_MODEL`). Use `OpenAIAugmentedLLM` for every agent. Verified: `augmented_llm_openai.py` constructs `AsyncOpenAI(api_key=..., base_url=...)` and uses Chat Completions with standard function calling — Nemotron's native tool calling slots in, no adapter.
4. **Build:** Orchestrator-Workers spawning schema-explorer / hypothesis-tester / chart-maker workers, all bound to CRAFT; wrap the analyst in Evaluator-Optimizer with a critic that rejects non-actionable findings.
5. **UI (~45 min):** thin Streamlit page rendering CRAFT's `generate_plotly_chart` JSON, or ship a markdown/HTML report artifact.

**Fallback:** the 2.5h estimate assumes plain API-key auth; budget +0.5–1h if only the Keycloak PKCE path is available. If auth wrangling exceeds 1h, lift the starter's token-mint code and pass the bearer as a static header.

---

### 3.2 evalstate/fast-agent — judging fit 8.5/10, ~2.5h

**What it is.** Declarative decorator-based MCP-native framework with built-in `chain`, `parallel`, `router`, `orchestrator`, `iterative_planner`, `evaluator_optimizer` workflow types. The most MCP-spec-complete client in the ecosystem. Apache-2.0, 3.9k stars, last commit **yesterday** (v0.9.5).

**Unique differentiator: native MCP OAuth2.1/PKCE support.** `MCPServerAuthSettings` drives `src/fast_agent/mcp/oauth_client.py` — dynamic client registration, local callback server on :3030 with paste-URL fallback, keyring token storage. If CRAFT enforces the Keycloak flow, this is the only candidate where auth works out of the box.

**Integration plan:**
1. `uv tool install fast-agent-mcp`; scaffold `fastagent.config.yaml` + secrets.
2. **CRAFT in:** `mcp.servers.craft: {transport: http, url: <CRAFT MCP URL>}` — OAuth handled automatically, or add headers for API-key mode. Agents take `servers=["craft"]` in the `@fast.agent` decorator; all eight CRAFT tools appear as native tools.
3. **Nebius in:** `generic: {base_url: <Token Factory endpoint>, api_key: <NEBIUS_KEY>}` — run agents with model string `generic.<nemotron-3-super-120b id>`. `GenericLLM` subclasses `OpenAILLM` with `parallel_tool_calls=True`; Nemotron's native function calling works unmodified. ~15 min.
4. **Build:** `chain(schema-scout → hypothesis-generator → parallel(sql-investigators) → evaluator_optimizer(insight-synthesizer))` in ~30 lines of decorators.

**Fallback:** if the framework learning curve bites, degrade gracefully — a single `@fast.agent` with `servers=["craft"]` and the generic Nebius model is a working entry in <1h.

---

### 3.3 langchain-ai/deepagents — judging fit 8.5/10, ~3h

**What it is.** Official LangChain deep-agent harness (26.1k stars, MIT, v0.6.12 Jun 25): `create_deep_agent(tools=..., model=...)` yields planning middleware (written todo plans), sub-agents with isolated contexts, a virtual filesystem for accumulating findings, and auto context summarization.

**Story bonus:** Nebius's own blog and NVIDIA's developer blog pair deepagents with Nemotron on Token Factory — "the harness the sponsor's own blueprint uses" is a near-free 20%+20% for architecture and story.

**Integration plan:**
1. `pip install deepagents langchain-mcp-adapters langchain-openai`.
2. **CRAFT in:**
   ```python
   from langchain_mcp_adapters.client import MultiServerMCPClient
   client = MultiServerMCPClient({"craft": {"transport": "streamable_http", "url": CRAFT_MCP_URL, "headers": {"Authorization": f"Bearer {CRAFT_API_KEY}"}}})
   tools = await client.get_tools()
   ```
3. **Nebius in:** `model=ChatOpenAI(model="<Nemotron-3 Super 120B id>", base_url="https://api.tokenfactory.nebius.com/v1", api_key=os.environ["NEBIUS_API_KEY"])`. ~15 min.
4. **Build:** parallel hypothesis sub-agents (pricing / refunds / segment mix / seasonality), each running its own CRAFT tool loop with `explain_error`/`get_hint` retries. Findings and chart JSON accumulate in the virtual filesystem; final step synthesizes them into a report.
5. **UI (~1h):** render a final HTML report embedding CRAFT's Plotly charts, or bolt a thin Streamlit chat over the LangGraph stream.

**Caveat:** the tuned Nebius profile targets Nemotron 3 **Ultra**, not the hackathon's Super 120B — in the pitch say "the Nemotron-tuned harness family."

## 4. Rejected / stretch candidates (summary)

- **openai/openai-agents-python** (27.8k, 8.5/10) — excellent, narrowly missed deep-dive cut; built-in tracing uploads to OpenAI servers (needs `set_tracing_disabled(True)` on pure Nebius). No OAuth edge over the top 3.
- **huggingface/smolagents** (28.3k, 8/10) — strong plan B; distinctive "agent writes Python to script CRAFT loops" demo; code-buried CRAFT calls are less judge-legible than named workflow patterns.
- **pydantic/pydantic-ai** (18.4k, 8/10) — built-in `NebiusProvider` and `MCPToolset(auth='oauth')`; loses on demo-readiness (no UI, investigation loop fully DIY).
- **langchain-mcp-adapters** (3.6k, 8/10) — not a standalone base; the glue layer used inside the deepagents plan (~10 lines wire all eight CRAFT tools into LangGraph).
- **mcp-use** (10.3k, 7/10) — fastest raw path to CRAFT-on-Nebius (~30–60 min), but pure plumbing; contributes nothing to insight or story scores.
- **ruc-datalab/DeepAnalyze** (4.3k, 6.5/10) — not MCP-native; fine-tune-specific tag loop means deep CRAFT wiring is a core rewrite (4.5h+ vs deadline). Cherry-pick its report-synthesis prompts instead.
- **crazycloud/data-analysis-llm-agent** (83, 6.5/10) — 2 years stale, zero MCP plumbing; useful only as a quarry for its Chainlit + inline `cl.Plotly` rendering pattern.
- **nebius/token-factory-cookbook langchain_data_agent_poc** (111, 4/10) — CRAFT would replace 5 of its 7 modules; quarry for prompt patterns and the "mirrors the sponsor's cookbook" story beat.
- **sqlchat/sqlchat** (5.8k, 4/10) — single-shot completion proxy; no agent loop, no tool calling, no chart lib; ~6h honest retrofit against a 4h deadline.
- **sinaptik-ai/pandas-ai** (23.6k, 4/10) — architecture collision with CRAFT; also mind the `pandasai/ee/` enterprise-license directory.

## 5. Recommendation

**Verdict: adapt an external framework as the agent brain, but keep the official starter's CRAFT connection plumbing.** The starter (`EmergenceAI/nebius-emergence-hackathon`) already solves the one genuinely risky integration — CRAFT's Keycloak OAuth2.1/PKCE auth in `mcp_starter.py` — but its flat single-loop agent leaves the 20% architecture criterion and much of the 30% CRAFT-depth criterion on the table.

**Primary path — lastmile-ai/mcp-agent (start now, T-4h):**

1. T-4:00 — CRAFT YAML block with API-key header; if key auth fails within 30 min, lift the bearer-mint from the starter's `mcp_starter.py`.
2. T-3:30 — Nebius via `OPENAI_BASE_URL`/`OPENAI_DEFAULT_MODEL` env; smoke-test one `generate_sql → execute_query` round trip on Nemotron.
3. T-3:00 — Build Orchestrator-Workers (schema-explorer, 3–4 hypothesis-tester workers, chart-maker) + Evaluator-Optimizer critic on the **e-commerce revenue anomaly** domain (unanimous best-domain pick across all 13 verified candidates).
4. T-1:15 — Thin Streamlit/HTML report rendering CRAFT's Plotly JSON.
5. T-0:30 — Rehearse the one-sentence story: *"Anthropic's Building Effective Agents patterns, composed over CRAFT, running entirely on Nemotron via Nebius Token Factory."*

**Auth fallback:** if mcp-agent's `MCPOAuthClientSettings` misbehaves, swap to **fast-agent** — its verified native PKCE client (`oauth_client.py`) is the field's only turnkey answer, and its decorator workflows are drop-in equivalents.

**Decision gate at T-2h — hedge path (enhance the official starter):** if CRAFT auth or framework friction has burned more than ~1.5h, abandon the framework and upgrade the starter in place: Gemini→Nebius swap (small, per the baseline), deepen its tool loop into an iterate-until-critic-approves cycle using `explain_error`/`get_hint`, and bolt on DeepAnalyze's multi-section report-synthesis prompt + the token-factory-cookbook's rewrite/route prompt patterns for analyst-grade narrative output. ~1.5–2h, zero integration risk.
