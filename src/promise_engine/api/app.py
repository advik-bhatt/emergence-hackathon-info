"""The Promise Engine's HTTP surface.

Everything analytical is built exactly once, at import time, off the committed fixtures — no
credentials or network calls are required to boot this app or serve a single request. The web
app in web/ is the actual deliverable; this module just gives it data to render.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from promise_engine.agent.loop import run_investigation
from promise_engine.agent.tools import Tools
from promise_engine.analysis.verdict import (
    MIN_TAIL_DAYS_FOR_FIX,
    OK_TOLERANCE_DAYS,
    VARIANCE_DOMINANT_SHARE,
)
from promise_engine.craft.cassette import Cassette

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = REPO_ROOT / "fixtures"
WEB_DIR = REPO_ROOT / "web"

# Built once, at import: every downstream request reuses these, none of them re-reads the
# fixtures or recomputes the analysis layer.
CASSETTE = Cassette(FIXTURES_DIR)
TOOLS = Tools.from_cassette(CASSETTE)
INVESTIGATION = run_investigation(CASSETTE)

app = FastAPI(title="The Promise Engine")


class PromiseRequest(BaseModel):
    seller_id: str
    state: str
    month: int | None = None
    seasonal: bool = False


@app.get("/runtime")
def get_runtime() -> dict[str, Any]:
    """What this deployment is actually wired to — the web HUD renders this verbatim."""
    import os

    return {
        "mode": os.environ.get("PROMISE_ENGINE_MODE", "replay"),
        "llm_configured": bool(os.environ.get("NEBIUS_API_KEY")),
        "model": os.environ.get("NEBIUS_MODEL", "moonshotai/Kimi-K2-Instruct"),
        "inference": "Nebius Token Factory",
        "data_plane": "Emergence CRAFT MCP",
        "mcp_url": os.environ.get("CRAFT_MCP_URL", "https://nebius.emergence.ai/mcp"),
        "steps": len(INVESTIGATION.steps),
        "hypotheses": len(INVESTIGATION.hypotheses),
        "verified_numbers": len(INVESTIGATION.computed),
        # decide()'s thresholds, so the web stress-test replays the same rule
        "verdict_rules": {
            "ok_tolerance_days": OK_TOLERANCE_DAYS,
            "variance_dominant_share": VARIANCE_DOMINANT_SHARE,
            "min_tail_days_for_fix": MIN_TAIL_DAYS_FOR_FIX,
        },
    }


@app.get("/receipts")
def get_receipts() -> dict[str, Any]:
    """Every number's provenance: the NL question asked of CRAFT and the SQL it generated."""
    receipts = {}
    for slug in ("lanes", "seasonality", "state_transit", "review_damage", "churn",
                 "seller_lateness"):
        rec = CASSETTE.replay(slug)
        receipts[slug] = {
            "nl_question": rec.nl_question,
            "sql": rec.sql,
            "columns": rec.columns,
            "rows": rec.rows,
        }
    return {"receipts": receipts}


@app.get("/seasonality")
def get_seasonality() -> dict[str, Any]:
    """Monthly order volume / promise / late-rate history for the calendar view."""
    return {"months": CASSETTE.replay("seasonality").as_dicts()}


@app.get("/lanes")
def get_lanes() -> dict[str, Any]:
    return {"lanes": TOOLS.rank_lanes()}


@app.get("/sellers")
def get_sellers() -> dict[str, Any]:
    sellers = sorted(
        TOOLS.engine.seller_handling.values(),
        key=lambda h: h.p95_handling_days,
        reverse=True,
    )
    return {
        "sellers": [
            {
                "seller_id": s.seller_id,
                "handling_p95_days": s.p95_handling_days,
                "median_handling_days": s.median_handling_days,
                "items": s.delivered_items,
            }
            for s in sellers
        ]
    }


@app.get("/investigation")
def get_investigation() -> dict[str, Any]:
    return {
        "hypotheses": INVESTIGATION.hypotheses,
        "narrative": INVESTIGATION.narrative,
        "steps": [
            {"tool": step.tool, "kind": step.kind, "finding": step.finding}
            for step in INVESTIGATION.steps
        ],
        "trap": INVESTIGATION.trap,
    }


@app.get("/states")
def get_states() -> dict[str, Any]:
    return {"states": sorted(TOOLS.engine.lanes.keys())}


@app.post("/promise")
def post_promise(body: PromiseRequest) -> dict[str, Any]:
    try:
        return TOOLS.compute_promise(
            seller_id=body.seller_id,
            state=body.state,
            month=body.month,
            seasonal=body.seasonal,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# Mounted last so the routes above take priority; html=True serves web/index.html at "/".
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
