"""Onboarding + workspace lifecycle routes."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.db import get_db
from core.security import get_current_user
from services.seed import build_demo_records
from services.detectors import run_all_detectors
from services.llm_analyst import _fallback_explanation


router = APIRouter(prefix="/api/workspace", tags=["workspace"])


class BusinessSetupInput(BaseModel):
    business_name: str = Field(min_length=1, max_length=120)
    industry: str = Field(min_length=1, max_length=80)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    load_demo_data: bool = True


async def _get_owned_workspace(user: dict) -> dict:
    db = get_db()
    ws = await db.workspaces.find_one(
        {"$or": [
            {"owner_user_id": user["user_id"]},
            {"invited_emails": user["email"]},
        ]},
        {"_id": 0},
    )
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return ws


async def _seed_workspace(workspace_id: str) -> int:
    """Seed the demo dataset AND produce rule-based signals with fallback
    explanations. LLM enrichment happens on-demand via /api/signals/refresh."""
    db = get_db()
    # Wipe any previous demo/signal data for a clean deterministic story.
    await db.financial_records.delete_many({"workspace_id": workspace_id})
    await db.signals.delete_many({"workspace_id": workspace_id})

    records = build_demo_records(workspace_id)
    if records:
        await db.financial_records.insert_many(records)

    signals = run_all_detectors(records)
    now = datetime.now(timezone.utc).isoformat()
    docs = []
    id_to_record = {r["record_id"]: r for r in records}
    for s in signals:
        evidence = [id_to_record[rid] for rid in s["evidence_record_ids"] if rid in id_to_record]
        fb = _fallback_explanation(s, evidence)
        docs.append({
            "signal_id": f"sig_{uuid.uuid4().hex[:12]}",
            "workspace_id": workspace_id,
            **s,
            "explanation": s.get("explanation") or fb["explanation"],
            "recommended_action": s.get("recommended_action") or fb["recommended_action"],
            "status": "open",
            "generated_by": "rule",
            "ai_enriched": False,
            "created_at": now,
            "resolved_at": None,
        })
    if docs:
        await db.signals.insert_many(docs)
    return len(records)


@router.get("/me")
async def get_my_workspace(current_user: dict = Depends(get_current_user)):
    ws = await _get_owned_workspace(current_user)
    db = get_db()
    counts = {
        "records": await db.financial_records.count_documents({"workspace_id": ws["workspace_id"]}),
        "demo_records": await db.financial_records.count_documents({
            "workspace_id": ws["workspace_id"], "source": "demo",
        }),
        "csv_records": await db.financial_records.count_documents({
            "workspace_id": ws["workspace_id"], "source": "csv",
        }),
        "signals": await db.signals.count_documents({"workspace_id": ws["workspace_id"]}),
    }
    return {"workspace": ws, "counts": counts}


@router.post("/setup")
async def business_setup(
    payload: BusinessSetupInput,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    ws = await _get_owned_workspace(current_user)
    if ws["owner_user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Only the workspace owner can complete setup.")

    updates = {
        "name": payload.business_name.strip(),
        "industry": payload.industry.strip(),
        "currency": payload.currency.upper(),
        "setup_completed_at": datetime.now(timezone.utc).isoformat(),
    }

    if payload.load_demo_data:
        n = await _seed_workspace(ws["workspace_id"])
        updates["is_seeded"] = True
        updates["data_source"] = "demo"
        updates["last_seeded_at"] = datetime.now(timezone.utc).isoformat()
    else:
        updates["is_seeded"] = False
        updates["data_source"] = "empty"
        n = 0

    await db.workspaces.update_one(
        {"workspace_id": ws["workspace_id"]},
        {"$set": updates},
    )
    ws = await db.workspaces.find_one({"workspace_id": ws["workspace_id"]}, {"_id": 0})
    return {"workspace": ws, "seeded_records": n}


@router.post("/reseed")
async def reseed(current_user: dict = Depends(get_current_user)):
    ws = await _get_owned_workspace(current_user)
    if ws["owner_user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Only the workspace owner can reseed.")
    n = await _seed_workspace(ws["workspace_id"])
    db = get_db()
    await db.workspaces.update_one(
        {"workspace_id": ws["workspace_id"]},
        {"$set": {
            "is_seeded": True,
            "data_source": "demo",
            "last_seeded_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"ok": True, "seeded_records": n}
