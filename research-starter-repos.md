# Starter-repo research (project research method pass)

Per the standing rule: given sponsors (Emergence CRAFT, Nebius Token Factory) + theme
(agentic data-intelligence over MCP), look for open-source repos that already fit, or that need
sponsor-tech grafted in.

## Best candidate: the official starter kit itself

**`EmergenceAI/nebius-emergence-hackathon`** (organizer-provided reference repo) already ships
two working, CRAFT-integrated agents plus a minimal starter file. This beats searching for
external highly-starred repos — it's sponsor-blessed and already wired to CRAFT MCP.

### What's in it

1. **Seller Delivery Intelligence Agent** — root-cause analysis over marketplace data.
   Python + **Claude** (Anthropic) + CRAFT MCP + Streamlit. Run: `streamlit run
   apps/seller_delivery_agent/app.py`.
2. **Customer Experience Intelligence Agent** — turns a customer ID into an engagement brief
   with recommendations/discounts. Python + **LangGraph** + CRAFT MCP + **Google Gemini**.
   Run: `python main.py <customer_id>`.
3. **`mcp_starter.py`** — single-file entry point: full OAuth 2.1/PKCE flow against Keycloak
   (`runtime.dev.emergence.ai`), CRAFT tool discovery, SQL generation, query execution. No
   agent framework required — good fallback if time runs out.

Auth: both agents go through the same Keycloak SSO instance. CRAFT MCP already does the
text-to-SQL heavy lifting (`list_databases` → `get_schema` → `generate_sql` → `execute_query`
→ `generate_plotly_chart`).

### The gap vs. this hackathon's judging

Neither shipped agent calls **Nebius Token Factory** — one uses Claude, the other Gemini. Since
"CRAFT usage depth" and presumably sponsor-stack usage matter for judging/per-challenge prizes,
and the CFP explicitly says "point [your agent] at Nebius for inference," the modification needed
is exactly the sponsor-integration described in the research-method rule.

**Easiest swap:** the LangGraph Customer Experience agent already uses a chat-model abstraction
(`langchain` style) — swapping its Gemini client for `langchain_openai.ChatOpenAI` pointed at
Nebius Token Factory's OpenAI-compatible endpoint (model: Nemotron-3 Super 120B) is a small,
localized change, not a rewrite. The Streamlit/Claude seller agent would need a bigger rework
(Anthropic SDK → OpenAI-compatible client).

## Other options considered

- **`nebius/token-factory-cookbook`** (official Nebius repo) — guides/examples for building on
  Token Factory; useful as a reference for the exact client init pattern, not a full agent.
- **`lastmile-ai/mcp-agent`** (~7.9k GitHub stars) — general-purpose, model-agnostic MCP agent
  orchestration framework (Parallel/Router/Orchestrator-Workers patterns). Strong "agent
  architecture" story if there's time to integrate CRAFT MCP + Nebius from scratch, but more
  setup work than adapting the starter kit under a hard deadline.
- **DBHub / QueryWeaver / Postgres MCP Pro / Google's MCP Toolbox for Databases** — popular
  text-to-SQL MCP servers, but redundant: CRAFT already *is* the text-to-SQL layer for this
  hackathon. Not needed.
- **`opencolin/claude-codex-nebius-proxy`** — local proxy that lets the Claude Code / Codex CLI
  route through Nebius's OpenAI-compatible API. Useful for *developing* with Nebius-backed Claude
  Code locally, not for the deployed agent's runtime inference calls (those should hit Nebius
  Token Factory directly).

## Recommendation

Fork/clone the Customer Experience Intelligence Agent (LangGraph + CRAFT MCP), swap its Gemini
client for an OpenAI-compatible client pointed at Nebius Token Factory (Nemotron-3 Super 120B),
and aim it at one of the 5 challenge domains. Falls back to `mcp_starter.py` if time is too short
for the full LangGraph app.
