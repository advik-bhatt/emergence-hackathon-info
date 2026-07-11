# Sponsor Environment Variables — Setup Steps

Three sponsors provide credentials you'll need before writing any agent code. Get all three
before the event; two of them (Nebius Token Factory + Tavily) come from the same Builder
Program flow.

---

## 1. Nebius Token Factory — `NEBIUS_API_KEY`

Nebius Token Factory is the OpenAI-compatible LLM inference endpoint for this hackathon.
Model: `nvidia/nemotron-3-super-120b-a12b`.

**Steps:**

1. Apply to the **Nebius Builder Program** at https://nebius.com/builder-program — describe
   your background and what you're building. Confirmed hackathon credits: $50 Token Factory +
   $50 Nebius AI Cloud.
2. Once approved, log in to the **Nebius Token Factory console** and generate an API key.
3. Export it:
   ```bash
   export NEBIUS_API_KEY=<your key>
   ```
4. Wire it into your agent framework using the OpenAI-compatible base URL:
   ```python
   base_url = "https://api.tokenfactory.nebius.com/v1/"
   # Authorization: Bearer <NEBIUS_API_KEY>
   ```

> If building with **Claude Agent SDK**, Nebius Token Factory does not host Anthropic models —
> you'll need a separate Anthropic API key for that framework's reasoning loop.

---

## 2. Nebius CRAFT MCP — `CRAFT_PROJECT_ID`

CRAFT is Emergence AI's text-to-SQL MCP server (hosted on Nebius infrastructure). It does not
use a static API key — access is OAuth-based, and every call is scoped to a project UUID
passed as the `X-Project-ID` header.

**Steps:**

1. Get your account allow-listed by submitting your Google or Microsoft email via the hackathon
   Luma page (see `luma-emergence-x-nebius.md`). Wait for the confirmation email.
2. Sign in at https://nebius.emergence.ai with Google or Microsoft.
3. After sign-in, your project UUID appears in the URL:
   `?projectId=edb5c0bf-5407-...`
4. Save it:
   ```bash
   export CRAFT_PROJECT_ID=<your project UUID>
   ```
5. Add it to your MCP client config as the `X-Project-ID` header (see
   `nebius-hackathon-prerequisites.md` for per-client snippets).

> `CRAFT_PROJECT_ID` is not a secret (it's a project identifier, not a credential), but store
> it alongside your other env vars for consistency.

---

## 3. Tavily — `TAVILY_API_KEY`

Tavily is the web-search API. The hackathon includes a $25 Tavily credit claimable via the
same Nebius Builder Program flow as the Token Factory credits.

**Steps:**

1. Claim your $25 credit via the **Nebius Builder Program** (same approval as Step 1 above —
   no separate application). The claim link is provided once approved.
2. Alternatively (or if credits aren't available yet), sign up for free at
   https://app.tavily.com — the free tier gives 1,000 searches/month, no credit card needed.
3. From the Tavily dashboard, copy your API key (starts with `tvly-`).
4. Export it:
   ```bash
   export TAVILY_API_KEY=tvly-<your key>
   ```
5. Call it directly — CRAFT does not proxy Tavily:
   ```python
   from tavily import TavilyClient
   client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
   results = client.search("your query")
   ```

---

## 4. Tenki.cloud — `TENKI_API_KEY`

Tenki.cloud provides disposable microVM sandboxes for agent code execution (boots in <2s),
plus fast GitHub Actions runners and AI code review. Useful if your agent needs to run
arbitrary code in isolation.

**Steps:**

1. Sign up at https://tenki.cloud and create a project.
2. From the dashboard, generate an API key (starts with `tk_`).
3. Export it:
   ```bash
   export TENKI_API_KEY=tk_<your key>
   ```
4. Optionally override the default base URL (only needed for self-hosted or staging):
   ```bash
   export TENKI_API_URL=https://api.tenki.cloud   # default; usually leave unset
   ```
5. Use via Go, TypeScript, or Python SDK — the SDK picks up `TENKI_API_KEY` automatically
   without any explicit `WithAuthToken()` call.

---

## Quick reference

| Sponsor | Env var | Format | Where to get it |
|---|---|---|---|
| Nebius Token Factory | `NEBIUS_API_KEY` | — | Nebius Token Factory console (via Builder Program) |
| Nebius CRAFT MCP | `CRAFT_PROJECT_ID` | UUID `xxxxxxxx-xxxx-...` | URL param after sign-in at nebius.emergence.ai |
| Tavily | `TAVILY_API_KEY` | `tvly-...` | app.tavily.com (or Builder Program credit claim) |
| Tenki.cloud | `TENKI_API_KEY` | `tk_...` | tenki.cloud dashboard |
| Tenki.cloud base URL | `TENKI_API_URL` | URL | Defaults to `https://api.tenki.cloud` — leave unset |

---

## Minimal `.env` template

```bash
# Nebius Token Factory (LLM inference)
NEBIUS_API_KEY=

# Emergence CRAFT MCP (text-to-SQL over Spider 2.0 DBs)
CRAFT_PROJECT_ID=

# Tavily (web search)
TAVILY_API_KEY=

# Tenki.cloud (agent sandboxes — optional)
TENKI_API_KEY=
```
