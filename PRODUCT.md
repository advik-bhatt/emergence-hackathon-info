# The Promise Engine

**Register:** product (demo-theater variant) — this is a hackathon stage demo. Design serves the pitch: every screen must land in under 5 seconds of judge attention.

## What it is

A delivery-promise auditor for Olist (real Brazilian marketplace data). It proves the promises Olist shows at checkout are mispriced per lane, decomposes the honest promise (seller handling + carrier transit + tail + season), springs "the trap" (the naive review-maximizing promise is unbounded — and we refuse it), and ships a ranked ops queue.

## Who sees it

Hackathon judges on a projector, then engineers reading the repo. Dark room, big screen, 3-minute pitch. The UI is the pitch.

## Stack truth (what badges may claim)

- Reasoning narrative: LLM via **Nebius Token Factory** (`NEBIUS_MODEL`, OpenAI-compatible). Falls back to a scripted investigation over the same tools without a key.
- Data plane: all SQL recorded from **Emergence CRAFT MCP** (`nebius.emergence.ai/mcp`) via `generate_sql`; replayed from committed fixtures.
- No conversion/revenue claims anywhere — Olist has no clickstream data.

## Design direction

**"Mission control for promises."** A logistics command center watching Brazil breathe. Dark theatre (near-black ink with a cold teal cast), phosphor-green primary signal, amber caution, signal-red for broken promises. Display type: Unbounded. Body: Instrument Sans. HUD numerals: IBM Plex Mono. Everything moves: the map idles, arcs fire, counters roll, the trap SPRINGS. Reduced-motion collapses to crossfades.

## Surfaces

1. **The Map** — full-viewport 3D extruded Brazil; hover raises states; click selects a lane; arcs + package particles fly from SP.
2. **Checkout simulator** — promise vs. engine, odometer numbers, animated decomposition, verdict stamp.
3. **Season calendar** — year×month heatmap with Brazilian retail holidays; click sets the sim month.
4. **Engine room** — the agent's reasoning trail as an animated tracing-beam graph: probe → probe → trap → refusal → resolution.
5. **The Trap** — the review curve draws itself, flattens, alarms UNBOUNDED, then the refusal.
6. **Ops queue** — gamified leaderboard ranked by orders at risk.
