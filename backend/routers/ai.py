"""AI ask endpoints — grounded Q&A (non-streaming + SSE streaming)."""
from __future__ import annotations
import asyncio
import json
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.db import get_db
from core.security import get_current_user, decode_token
from services.finance import compute_kpis, format_amount_exact
from services.llm_analyst import (
    stream_ask,
    _brief_for_ask,
    _chat,
    _collect,
    build_ask_system,
)


router = APIRouter(prefix="/api/ai", tags=["ai"])


async def _wid_and_currency(user: dict) -> tuple[str, str]:
    db = get_db()
    ws = await db.workspaces.find_one(
        {"$or": [
            {"owner_user_id": user["user_id"]},
            {"invited_emails": user["email"]},
        ]},
        {"_id": 0, "workspace_id": 1, "currency": 1},
    )
    if not ws:
        raise HTTPException(status_code=404, detail="No workspace.")
    return ws["workspace_id"], ws.get("currency", "USD")


async def _wid(user: dict) -> str:
    wid, _ = await _wid_and_currency(user)
    return wid


async def _load_context(wid: str):
    db = get_db()
    records = await db.financial_records.find({"workspace_id": wid}, {"_id": 0}).to_list(500)
    signals = await db.signals.find({"workspace_id": wid}, {"_id": 0}).to_list(200)
    kpis = compute_kpis(records, signals)
    return records, signals, kpis


async def _resolve_citations(wid: str, text: str, currency: str = "USD"):
    """Return (filtered_text, citations[]) — dead [rec:...] tokens stripped
    AND internal brief/JSON field names scrubbed out of the answer so they
    never leak to a CFO-facing surface."""
    cited_ids = list(set(re.findall(r"\[rec:([a-zA-Z0-9_\-]+)\]", text)))
    citations: list = []
    valid_ids: set = set()
    if cited_ids:
        db = get_db()
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
                "amount_display": format_amount_exact(r.get("amount", 0), currency),
                "counterparty": r["counterparty"],
                "memo": r.get("memo"),
            })
    filtered = re.sub(
        r"\[rec:([a-zA-Z0-9_\-]+)\]",
        lambda m: m.group(0) if m.group(1) in valid_ids else "",
        text,
    )
    filtered = _scrub_internal_terms(filtered)
    return filtered, citations


# Deterministic replacement of internal field/data-shape names that must
# never appear in analyst answers.
_INTERNAL_TERM_SUBS = [
    (re.compile(r"\bprior_recovery_available\b", re.IGNORECASE), "prior-recovery data"),
    (re.compile(r"\bdataset_facts\b", re.IGNORECASE), "the current dataset"),
    (re.compile(r"\bthe brief\b", re.IGNORECASE), "the current dataset"),
    (re.compile(r"\bthis brief\b", re.IGNORECASE), "the current dataset"),
    (re.compile(r"\bthe JSON( brief)?\b", re.IGNORECASE), "the current dataset"),
    (re.compile(r"\btop_signals\b", re.IGNORECASE), "top findings"),
    (re.compile(r"\bsample_records\b", re.IGNORECASE), "sampled records"),
]


def _scrub_internal_terms(text: str) -> str:
    for pattern, replacement in _INTERNAL_TERM_SUBS:
        text = pattern.sub(replacement, text)
    return text


class AskInput(BaseModel):
    question: str = Field(min_length=2, max_length=800)


@router.post("/ask")
async def ask(payload: AskInput, current_user: dict = Depends(get_current_user)):
    """Non-streaming Q&A — returns {"answer": str, "citations": [record_ids]}."""
    wid, currency = await _wid_and_currency(current_user)
    records, signals, kpis = await _load_context(wid)

    brief = _brief_for_ask(kpis, signals, records, currency)
    prompt = (
        "Answer the CFO's question using ONLY the brief below. Cite record_ids "
        "inline as [rec:<id>]. Keep the answer under ~180 words unless the "
        "question demands more. Remember: the brief's `dataset_facts` block "
        "contains the ONLY prior-recovery figure that exists — if "
        "`prior_recovery_available` is false, do not claim any money has been "
        "recovered previously.\n\n"
        f"Question: {payload.question}\n\n"
        f"Brief:\n{json.dumps(brief)[:80_000]}"
    )
    chat = _chat(
        session_id=f"ask-{current_user['user_id']}",
        system=build_ask_system(currency),
    )
    try:
        text = await _collect(chat, prompt)
    except Exception as e:
        print(f"[/api/ai/ask] error: {e}")
        text = (
            "I couldn't reach the analysis service just now. The signals on this "
            "page remain valid — try the question again in a moment."
        )

    filtered, citations = await _resolve_citations(wid, text, currency)
    return {"answer": filtered, "citations": citations}


# ---------------------------------------------------------------------------
# SSE streaming variant — token-by-token
# ---------------------------------------------------------------------------

async def _current_user_from_query(token: str = Query(...)) -> dict:
    """Auth helper for SSE clients that can't set the Authorization header
    (browser EventSource). We validate the same JWT format and return the
    same shape as `get_current_user`."""
    import jwt as _jwt
    try:
        payload = decode_token(token)
    except _jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except _jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    db = get_db()
    user = await db.users.find_one({"user_id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.get("/ask/stream")
async def ask_stream(
    question: str = Query(..., min_length=2, max_length=800),
    current_user: dict = Depends(_current_user_from_query),
):
    """SSE stream:
       event: delta   data: {"text": "..."}
       event: done    data: {"citations": [...]}
       event: error   data: {"detail": "..."}
    """
    wid, currency = await _wid_and_currency(current_user)
    records, signals, kpis = await _load_context(wid)

    async def _generate():
        # Send a hello event so clients know we're live even before Claude
        # ships the first token.
        yield "event: open\ndata: {}\n\n"

        collected_parts: list[str] = []
        try:
            async for chunk in stream_ask(
                session_id=f"ask-stream-{current_user['user_id']}",
                question=question,
                kpis=kpis,
                signals=signals,
                records=records,
                currency=currency,
            ):
                if not chunk:
                    continue
                collected_parts.append(chunk)
                yield f"event: delta\ndata: {json.dumps({'text': chunk})}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'detail': str(exc)})}\n\n"
            return

        full_text = "".join(collected_parts).strip()
        filtered, citations = await _resolve_citations(wid, full_text, currency)
        # Send corrected text (dead tokens stripped) so the client can render
        # a clean final version, then the citation list.
        final_payload = {"text": filtered, "citations": citations}
        yield f"event: done\ndata: {json.dumps(final_payload)}\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
