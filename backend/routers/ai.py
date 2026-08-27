"""AI ask-anything endpoint — SSE streaming grounded in workspace data."""
from __future__ import annotations
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.db import get_db
from core.security import get_current_user, decode_token
from services.finance import compute_kpis
from services.llm_analyst import stream_ask


router = APIRouter(prefix="/api/ai", tags=["ai"])


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


class AskInput(BaseModel):
    question: str = Field(min_length=2, max_length=800)


@router.post("/ask")
async def ask(payload: AskInput, current_user: dict = Depends(get_current_user)):
    """Non-streaming Q&A — returns {"answer": str, "citations": [record_ids]}."""
    from services.llm_analyst import _collect, _chat, ASK_SYSTEM, _brief_for_ask

    db = get_db()
    wid = await _wid(current_user)
    records = await db.financial_records.find({"workspace_id": wid}, {"_id": 0}).to_list(500)
    signals = await db.signals.find({"workspace_id": wid}, {"_id": 0}).to_list(200)
    kpis = compute_kpis(records, signals)

    brief = _brief_for_ask(kpis, signals, records)
    prompt = (
        "Answer the CFO's question using ONLY the brief below. Cite record_ids "
        "inline as [rec:<id>]. Keep the answer under ~180 words unless the "
        "question demands more.\n\n"
        f"Question: {payload.question}\n\n"
        f"Brief:\n{json.dumps(brief)[:80_000]}"
    )
    chat = _chat(session_id=f"ask-{current_user['user_id']}", system=ASK_SYSTEM)
    try:
        text = await _collect(chat, prompt)
    except Exception as e:
        print(f"[/api/ai/ask] error: {e}")
        text = (
            "I couldn't reach the analysis service just now. The signals on this "
            "page remain valid — try the question again in a moment."
        )

    # Extract cited record IDs from [rec:...] markers, then FILTER to only
    # tokens that resolve to an actual record in this workspace — so hallucinated
    # or misclassified ids never surface to the UI.
    import re
    cited_ids = list(set(re.findall(r"\[rec:([a-zA-Z0-9_\-]+)\]", text)))
    citations = []
    valid_ids = set()
    if cited_ids:
        cursor = db.financial_records.find(
            {"workspace_id": wid, "record_id": {"$in": cited_ids}}, {"_id": 0}
        )
        async for r in cursor:
            valid_ids.add(r["record_id"])
            citations.append({
                "record_id": r["record_id"],
                "type": r["type"],
                "date": r["date"],
                "amount": r["amount"],
                "counterparty": r["counterparty"],
                "memo": r.get("memo"),
            })

    # Strip any [rec:...] tokens that don't resolve to a real record so the
    # frontend never renders dead citation chips.
    def _keep(m):
        return m.group(0) if m.group(1) in valid_ids else ""
    text = re.sub(r"\[rec:([a-zA-Z0-9_\-]+)\]", _keep, text)

    return {"answer": text, "citations": citations}
