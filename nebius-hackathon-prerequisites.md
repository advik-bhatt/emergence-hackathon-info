# Nebius Hackathon — Prerequisites Checklist

Read this before the event. Do everything in this checklist ahead of time so you spend
hackathon day building an agent, not debugging OAuth. Total time: ~15 minutes once your account
is provisioned.

**Community:** Join the EmergenceAI Community Slack, then head to `#hack`. Join before the
event, not during a live-fire debugging session.

**Support:** All hackathon support and office hours happen in `#hack` on the Emergence AI
Community Slack.

---

## 1. Get your account provisioned

CRAFT's hackathon environment uses your existing Google or Microsoft identity — there's no
separate password to create. Provisioning is allow-list based, so do this first; it's the only
step with a lead time you don't control.

1. Submit your Google or Microsoft account email via the Enterprise Agents Hackathon — By
   Emergence, in partnership with Nebius (NYC) Luma page
2. Wait for your confirmation email. Allow-list reviews run in batches — if you haven't heard
   back within a few business days, ask in `#hack`
3. Do not try to sign in before you get the confirmation — you'll hit a 403 and have to retry
   later

---

## 2. Find your Project ID

Every API call to CRAFT is scoped to a project via the `X-Project-ID` header. You get this
once, from the browser, after your first sign-in.

1. Go to https://nebius.emergence.ai and sign in with **Sign in with Google** or **Sign in with
   Microsoft**, using the account you registered with
2. Once logged in, your first project is auto-selected and appended to the URL:
   `?projectId=<uuid>`
3. Copy that UUID — it starts with e.g. `edb5c0bf-5407-...`, not `em_hk_...` or any other
   prefix. You'll paste it into every MCP client config below.

> If you land on a "no projects" screen instead of a `projectId` in the URL, your account was
> allow-listed but a project hasn't been assigned yet — ping `#hack`, don't try to self-serve a
> project creation.

---

## 3. Install an MCP client

Pick one to start (you can add more later). All of them speak the same protocol — Streamable
HTTP + OAuth 2.1 (Authorization Code + PKCE) — so the differences below are purely in where you
paste the config, not what the config means.

**What every config below has in common:**

| Field | Value | What it's for |
|---|---|---|
| `url` | `https://nebius.emergence.ai/mcp` | The MCP endpoint. Use this exact hostname |
| `headers.X-Project-ID` | your UUID from Step 2 | Scopes every tool call to your project |
| `oauth.clientId` | `em-runtime-mcp` | The public OAuth client (no secret — PKCE) |
| `oauth.authServerMetadataUrl` | `https://runtime.prod.emergence.ai/keycloak/realms/hub/.well-known/openid-configuration` | Where your client discovers the login flow |
| `oauth.callbackPort` | `9876` | Local port your client listens on during the browser login redirect. Free it first if needed (`lsof -ti:9876 \| xargs kill`) |
| `oauth.scopes` | `openid profile email organization` | Standard identity scopes; `organization` carries your project/org membership into the token |

### Claude Code

```sh
claude mcp add-json Craft '{
  "type": "http",
  "url": "https://nebius.emergence.ai/mcp",
  "headers": {
    "X-Project-ID": "<your project UUID>"
  },
  "oauth": {
    "clientId": "em-runtime-mcp",
    "authServerMetadataUrl": "https://runtime.prod.emergence.ai/keycloak/realms/hub/.well-known/openid-configuration",
    "callbackPort": 9876,
    "scopes": "openid profile email organization"
  }
}'
```

- Run the command above (or manually edit `~/.claude.json` under `mcpServers`)
- Claude Code requires **2.1.179 or later** for OAuth over HTTP transport — older versions fail
  silently. Check with `claude --version`; upgrade with `npm install -g @anthropic-ai/claude-code`
- Invoke any tool (e.g. ask "list the available databases") — the first call triggers the
  browser OAuth flow automatically

### VS Code

Open the Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`) → **MCP: Open User Configuration**
(opens `mcp.json`, macOS: `~/Library/Application Support/Code/User/mcp.json`), then add:

```json
{
  "servers": {
    "Craft": {
      "url": "https://nebius.emergence.ai/mcp",
      "type": "http",
      "headers": {
        "X-Project-ID": "<your project UUID>"
      },
      "oauth": {
        "clientId": "em-runtime-mcp",
        "callbackPort": 9876,
        "authServerMetadataUrl": "https://runtime.prod.emergence.ai/keycloak/realms/hub/.well-known/openid-configuration",
        "scopes": "openid profile email organization"
      }
    }
  },
  "inputs": []
}
```

> VS Code's schema uses a top-level `servers` key, not `mcpServers` — a common copy-paste
> mistake when porting a Claude Code config.

Save, reopen the Command Palette → **MCP: List Servers** → select **Craft** → **Start**. A
browser window opens for OAuth login. Verify via **MCP: List Resources** or by asking a question
in chat that needs a tool call.

### Cursor

Add to `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "Craft": {
      "type": "http",
      "url": "https://nebius.emergence.ai/mcp",
      "headers": {
        "X-Project-ID": "<your project UUID>"
      },
      "auth": {
        "CLIENT_ID": "em-runtime-mcp",
        "scopes": ["openid", "profile", "email", "organization"]
      }
    }
  }
}
```

Cursor discovers the OAuth requirement automatically from the server (no `oauth` block needed)
and opens a browser to complete Authorization Code + PKCE the first time you use a tool.

> **Known caveat:** Cursor has an open bug where, once it detects OAuth via server discovery,
> it can ignore the `headers` block entirely — your `X-Project-ID` header may silently not be
> sent, and calls fail with a project-scoping error rather than an auth error. If tools connect
> but every call errors on missing/invalid project context, this is the likely cause — flag it
> in `#hack` and fall back to VS Code or Claude Code if it isn't fixed by then.

### Gemini CLI

Add to `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "Craft": {
      "httpUrl": "https://nebius.emergence.ai/mcp",
      "headers": {
        "X-Project-ID": "<your project UUID>"
      },
      "oauth": {
        "enabled": true,
        "clientId": "em-runtime-mcp",
        "authorizationUrl": "https://runtime.prod.emergence.ai/keycloak/realms/hub/protocol/openid-connect/auth",
        "tokenUrl": "https://runtime.prod.emergence.ai/keycloak/realms/hub/protocol/openid-connect/token",
        "redirectUri": "http://localhost:9876/oauth/callback",
        "scopes": ["openid", "profile", "email", "organization"]
      }
    }
  }
}
```

Leave `authProviderType` unset — it defaults to `dynamic_discovery`, which finds the Keycloak
OAuth flow automatically. Authenticate with `/mcp auth Craft` inside the session, or just invoke
a tool and follow the browser prompt.

> Headless/SSH note: OAuth needs a local browser. If remote, authenticate once on a machine with
> a browser, then copy `~/.gemini/mcp-oauth-tokens.json` to the remote machine. This combination
> is less battle-tested than Claude Code/VS Code — verify with Step 4 before relying on it.

### Codex CLI (OpenAI)

Add to `~/.codex/config.toml`:

```toml
mcp_oauth_callback_port = 9876

[mcp_servers.Craft]
url = "https://nebius.emergence.ai/mcp"
scopes = ["openid", "profile", "email", "organization"]

[mcp_servers.Craft.http_headers]
X-Project-ID = "<your project UUID>"

[mcp_servers.Craft.oauth]
client_id = "em-runtime-mcp"
```

Run `codex mcp login craft` — opens a browser for the Keycloak OAuth flow and caches the token;
static headers and OAuth are independent here, so both apply together. `codex mcp logout craft`
to revoke and re-auth if needed. OAuth login requires a local browser — not available in a fully
headless environment.

### Other MCP clients (Cline, custom frameworks, etc.)

Any client that supports Streamable HTTP transport + OAuth 2.1 (Authorization Code + PKCE) +
custom request headers works. Point it at:

- **URL:** `https://nebius.emergence.ai/mcp`
- **Header:** `X-Project-ID: <your project UUID>`
- **OAuth:** discover via `https://runtime.prod.emergence.ai/keycloak/realms/hub/.well-known/openid-configuration`,
  client ID `em-runtime-mcp`, PKCE (no client secret), scopes `openid profile email organization`

---

## 4. Verify your connection

Before the event, confirm end-to-end connectivity — don't wait until hackathon morning:

1. Call the `hello_world` tool (pure sanity check, no upstream dependencies) — if this fails,
   it's an auth/connectivity problem, not a data problem
2. Call `list_databases` and confirm you see catalog entries — this exercises your
   `X-Project-ID` header. If `hello_world` works but `list_databases` errors or returns empty,
   your header likely isn't reaching the server
3. If both work, you're fully connected

- **401** → re-run OAuth login (cached tokens can go stale)
- **403 or empty results with no error** → project isn't provisioned yet, ping `#hack`

---

## 5. Available tools

Tools show up in your client as `<tool-name>` or `mcp__<server-name>__<tool-name>` depending on
the client. There are no `spider2_/codegen_/dx_/plotly_` prefixes — that naming was from an
earlier design and did not ship.

| Tool | What it does |
|---|---|
| `hello_world` | Sanity check |
| `list_databases` | List database metadata in your project's catalog |
| `get_schema` | DDL / metadata for a database, schema, or table by fully-qualified name |
| `search_schema` | Full-text search across catalog metadata (filter by asset type, connection, FQN prefix) |
| `generate_sql` | Natural language → SQL. This is the core value prop — let it write the SQL, don't hand-write queries |
| `execute_query` | Run a read-only SQL statement, get rows back |
| `resolve_term` | Look up a business term (e.g. "conversion rate") against domain knowledge |
| `generate_plotly_chart` | Tabular data → Plotly chart spec |
| `sample_data` | Preview rows from a table |
| `get_result_page` | Paginate through a previously executed query's results |

> If a Talk2Data tool returns `{"ok": false, "error": {"code": "talk2data_not_configured"}}`,
> that's a server-side config gap, not something on your end — catalog tools (`list_databases`,
> `get_schema`, `search_schema`) are unaffected.

---

## 6. Choose your agent framework

Any framework works — Claude Agent SDK, Google ADK, LangGraph, Pydantic AI, CrewAI, or
hand-rolled. The MCP server doesn't care what's calling it.

| Framework | MCP client support | LLM wiring |
|---|---|---|
| Claude Agent SDK | Native MCP support (`mcp_servers` config) | Anthropic API — not covered by Nebius Token Factory credits |
| Google ADK | Native MCP tool support | Any OpenAI-compatible endpoint, incl. Nebius Token Factory, or Gemini directly |
| LangGraph | `langchain-mcp-adapters` or manual MCP client | Any OpenAI-compatible endpoint, incl. Nebius Token Factory |
| Pydantic AI | Native MCP support (`MCPServerStreamableHTTP`) | Any OpenAI-compatible endpoint, incl. Nebius Token Factory |
| Custom / raw MCP SDK | `mcp` Python/TS SDK client directly | Whatever you wire up |

---

## 7. Get LLM access — Nebius Token Factory or your own key

Your agent's reasoning LLM is separate from CRAFT's own SQL-generation LLM (`generate_sql` uses
its own backend — you don't need an LLM key just to call CRAFT tools). You only need an LLM for
your agent's own orchestration/reasoning loop.

1. **Request credits** via the Nebius Builder Program (apply, describe your background/use
   case). Confirmed credits as of 2026-07-09: $50 Nebius Token Factory + $50 Nebius AI Cloud
   + $25 Tavily + a $1 Nebius Academy certification offer.
2. Once approved, get your API key from the Nebius Token Factory console.
3. Nebius Token Factory is OpenAI-API-compatible:
   - `base_url = https://api.tokenfactory.nebius.com/v1/`
   - Standard `Authorization: Bearer <key>`
   - Plugs directly into LangGraph, Pydantic AI, Google ADK, or any OpenAI-client-based agent
4. **Recommended model:** `nvidia/nemotron-3-super-120b-a12b` — 120B params (12B active, hybrid
   MoE), up to 1M context, native function calling, OpenAI-compatible
5. The $25 Tavily credit is a bonus for this hackathon — grab that key from the same
   builder-program claim flow (call Tavily directly for web search; CRAFT doesn't proxy it)

> If building with Claude Agent SDK specifically, Nebius Token Factory does not host Anthropic
> models — you'll need your own Anthropic API key for that framework's reasoning loop.

**Standard (non-credit) Token Factory pricing:** ~$0.30/1M input, ~$0.90/1M output tokens for
Nemotron 3 Super.

---

## 8. Know the data — Spider 2.0 subset (9 databases, ~37 GB)

CRAFT pre-loads 9 enterprise databases from the Spider 2.0 benchmark (ICLR 2025 Oral), grouped
into 5 challenge scenarios. You don't need to know SQL — `generate_sql` handles it, including
the hardest patterns (`LATERAL FLATTEN`, multi-schema JOINs, nested VARIANT extraction).

| # | Databases | Size / scale | Difficulty | The hook |
|---|---|---|---|---|
| 1 | THELOOK_ECOMMERCE (7 tables, 3.3M rows) + BRAZILIAN_E_COMMERCE (10 tables, 1.6M rows) | 0.2 GB | Beginner → Intermediate | Clean synthetic + real marketplace data — a customer-insights agent investigating churn hypotheses |
| 2 | CRYPTO — 7 blockchain schemas, 39 tables, 158M rows | 30.4 GB | Intermediate → Advanced | Spider 2.0's most question-rich database — cross-chain compliance/risk investigation |
| 3 | IDC (16 tables, 4.8M rows) + PANCANCER_ATLAS_1 (10 tables, 18.9M rows) | 1.8 GB | Intermediate → Advanced | DICOM imaging metadata + cancer genomics — CRAFT resolves the medical terminology for you |
| 4 | GA4 (92 daily-partitioned tables, 4.3M rows) + FIREBASE (114 tables, 5.7M rows) | 1.2 GB | Advanced | Nested VARIANT/ARRAY columns requiring LATERAL FLATTEN — most NL-to-SQL systems fail here |
| 5 | GITHUB_REPOS (6 tables, 7.6M rows) + DEPS_DEV_V1 (10 tables, 80M rows) | 3.7 GB | Intermediate | Repo metadata + package dependency graph — supply-chain vulnerability blast-radius investigation |

Total: 9 databases, ~37 GB. All queries run read-only against Snowflake — DDL/DML is rejected.

**Rate limits:** metadata tools 30/min, query execution 10/min per key.

---

## 9. Known gaps

- **MCP is the only interface.** A2A multi-agent endpoints, a Python SDK (`craft-sdk`), and a
  REST API are planned — don't build a submission that depends on them
- **Nemotron-3 Super integration** — CRAFT's own `generate_sql` currently runs on GCP Vertex
  AI, not Nebius Token Factory. This is a separate, in-progress workstream — it doesn't affect
  your ability to use Nebius Token Factory for your own agent's LLM (Step 7)
