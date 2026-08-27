"""Signals API — list, filter, mark actioned, and enrich with LLM."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.db import get_db
from core.security import get_current_user
from services.finance import CATEGORY_LABEL, CATEGORY_TONE, format_currency
from services.llm_analyst import explain_signal


router = APIRouter(prefix="/api/signals", tags=["signals"])


async def _wid(user: dict) -> str:
    db = get_db()
    ws = await db.workspaces.find_one(
        {"$or": [
            {"owner_user_id": user["user_id"]},
            {"invited_emails": user["email"]},
        ]},
        {"_id": 0, "workspace_id": 1},
    )
    if not ws:
        raise HTTPException(status_code=404, detail="No workspace.")
    return ws["workspace_id"]


def _serialize(sig: dict, evidence: list[dict]) -> dict:
    return {
        "signal_id": sig["signal_id"],
        "title": sig["title"],
        "category": sig["category"],
        "category_label": CATEGORY_LABEL.get(sig["category"], sig["category"]),
        "tone": CATEGORY_TONE.get(sig["category"], "warning"),
        "detector": sig["detector"],
        "impact_amount": sig["impact_amount"],
        "impact_display": format_currency(sig["impact_amount"]),
        "amount_type": sig["amount_type"],
        "confidence": sig["confidence"],
        "urgency": sig["urgency"],
        "priority_score": sig["priority_score"],
        "status": sig.get("status", "open"),
        "explanation": sig.get("explanation", ""),
        "recommended_action": sig.get("recommended_action", ""),
        "ai_enriched": bool(sig.get("ai_enriched")),
        "created_at": sig.get("created_at"),
        "resolved_at": sig.get("resolved_at"),
        "evidence_record_ids": sig.get("evidence_record_ids", []),
        "evidence": [
            {
                "record_id": r["record_id"],
                "type": r["type"],
                "date": r["date"],
                "amount": r["amount"],
                "amount_display": format_currency(r["amount"]),
                "counterparty": r["counterparty"],
                "memo": r.get("memo"),
                "status": r.get("status"),
                "source": r.get("source"),
            }
            for r in evidence
        ],
    }


@router.get("")
async def list_signals(
    category: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    wid = await _wid(current_user)
    q: dict = {"workspace_id": wid}
    if category:
        q["category"] = category
    if status:
        q["status"] = status

    sigs = await db.signals.find(q, {"_id": 0}).to_list(limit)
    sigs.sort(key=lambda s: float(s.get("priority_score", 0)), reverse=True)

    # Batch-fetch evidence records
    all_ids = {rid for s in sigs for rid in s.get("evidence_record_ids", [])}
    ev_map: dict = {}
    if all_ids:
        cursor = db.financial_records.find(
            {"workspace_id": wid, "record_id": {"$in": list(all_ids)}}, {"_id": 0}
        )
        async for r in cursor:
            ev_map[r["record_id"]] = r

    out = []
    for s in sigs[:limit]:
        ev = [ev_map[rid] for rid in s.get("evidence_record_ids", []) if rid in ev_map]
        out.append(_serialize(s, ev))
    return {"signals": out, "total": len(out)}


@router.get("/{signal_id}")
async def get_signal(signal_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    wid = await _wid(current_user)
    s = await db.signals.find_one({"workspace_id": wid, "signal_id": signal_id}, {"_id": 0})
    if not s:
        raise HTTPException(status_code=404, detail="Signal not found.")
    ev = await db.financial_records.find(
        {"workspace_id": wid, "record_id": {"$in": s.get("evidence_record_ids", [])}},
        {"_id": 0},
    ).to_list(50)
    return _serialize(s, ev)


class StatusInput(BaseModel):
    status: str  # open | in_progress | resolved | dismissed


@router.post("/{signal_id}/status")
async def update_status(
    signal_id: str,
    payload: StatusInput,
    current_user: dict = Depends(get_current_user),
):
    allowed = {"open", "in_progress", "resolved", "dismissed"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(allowed)}")
    db = get_db()
    wid = await _wid(current_user)
    update = {"status": payload.status}
    if payload.status == "resolved":
        update["resolved_at"] = datetime.now(timezone.utc).isoformat()
    else:
        update["resolved_at"] = None
    res = await db.signals.update_one(
        {"workspace_id": wid, "signal_id": signal_id},
        {"$set": update},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Signal not found.")
    return {"ok": True}


@router.post("/enrich")
async def enrich_all_signals(current_user: dict = Depends(get_current_user)):
    """Rewrite explanations + recommended actions using the LLM analyst.
    Idempotent — signals already marked ai_enriched are skipped."""
    db = get_db()
    wid = await _wid(current_user)
    sigs = await db.signals.find(
        {
            "workspace_id": wid,
            "ai_enriched": {"$ne": True},
            "status": "open",
        },
        {"_id": 0},
    ).to_list(50)

    id_to_ev = {}
    all_ids = {rid for s in sigs for rid in s.get("evidence_record_ids", [])}
    if all_ids:
        async for r in db.financial_records.find(
            {"workspace_id": wid, "record_id": {"$in": list(all_ids)}}, {"_id": 0}
        ):
            id_to_ev[r["record_id"]] = r

    async def _do(s: dict):
        ev = [id_to_ev[i] for i in s.get("evidence_record_ids", []) if i in id_to_ev]
        session = f"signal-{s['signal_id']}"
        try:
            result = await explain_signal(session, s, ev)
        except Exception as exc:
            print(f"[enrich] llm error: {exc}")
            return
        await db.signals.update_one(
            {"workspace_id": wid, "signal_id": s["signal_id"]},
            {"$set": {
                "explanation": result["explanation"] or s.get("explanation"),
                "recommended_action": result["recommended_action"] or s.get("recommended_action"),
                "ai_enriched": True,
                "enriched_at": datetime.now(timezone.utc).isoformat(),
            }},
        )

    # Cap parallelism so we don't hammer the LLM
    sem = asyncio.Semaphore(3)

    async def _bounded(s: dict):
        async with sem:
            await _do(s)

    await asyncio.gather(*[_bounded(s) for s in sigs])
    return {"enriched": len(sigs)}
