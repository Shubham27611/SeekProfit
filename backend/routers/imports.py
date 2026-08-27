"""CSV import — 'Replace with your CSV' workflow."""
from __future__ import annotations
import csv
import io
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from core.db import get_db
from core.security import get_current_user
from services.detectors import run_all_detectors
from services.llm_analyst import _fallback_explanation


router = APIRouter(prefix="/api/imports", tags=["imports"])

TYPE_ALIASES = {
    "invoice": "invoice", "sales_invoice": "invoice", "bill_customer": "invoice",
    "vendor_bill": "vendor_bill", "bill": "vendor_bill", "expense": "vendor_bill",
    "payment": "payment", "receipt": "payment",
    "contract": "contract", "subscription": "contract",
    "refund": "refund",
}


async def _wid(user: dict) -> str:
    db = get_db()
    ws = await db.workspaces.find_one(
        {"$or": [
            {"owner_user_id": user["user_id"]},
            {"invited_emails": user["email"]},
        ]},
        {"_id": 0, "workspace_id": 1, "owner_user_id": 1},
    )
    if not ws:
        raise HTTPException(status_code=404, detail="No workspace.")
    if ws.get("owner_user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Only the workspace owner can import data.")
    return ws["workspace_id"]


def _parse_csv(raw: bytes) -> List[dict]:
    """Accept flexible CSV column names, map to our schema."""
    df = pd.read_csv(io.BytesIO(raw))
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    required_any = ({"type", "date", "amount", "counterparty"}, {"txn_type", "date", "amount", "party"})
    cols = set(df.columns)
    if not any(req.issubset(cols) for req in required_any):
        raise HTTPException(
            status_code=400,
            detail=(
                "CSV must include at least: type, date, amount, counterparty. "
                "Optional: memo, status, currency."
            ),
        )

    if "txn_type" in cols and "type" not in cols:
        df = df.rename(columns={"txn_type": "type"})
    if "party" in cols and "counterparty" not in cols:
        df = df.rename(columns={"party": "counterparty"})

    out = []
    for _, row in df.iterrows():
        try:
            raw_type = str(row["type"]).strip().lower()
            t = TYPE_ALIASES.get(raw_type)
            if not t:
                continue
            amount = float(row["amount"])
            date = pd.to_datetime(row["date"]).to_pydatetime()
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            rec = {
                "record_id": f"csv_{uuid.uuid4().hex[:10]}",
                "type": t,
                "date": date.isoformat(),
                "amount": amount,
                "currency": str(row.get("currency", "USD") or "USD").upper()[:3],
                "counterparty": str(row["counterparty"]).strip(),
                "memo": str(row.get("memo", "") or ""),
                "status": str(row.get("status", "") or "").strip().lower() or "unknown",
                "source": "csv",
                "raw": {},
            }
            out.append(rec)
        except Exception:
            continue
    if not out:
        raise HTTPException(status_code=400, detail="No valid rows found in CSV.")
    return out


@router.post("/csv")
async def upload_csv(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if not (file.filename or "").lower().endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (5MB limit).")

    wid = await _wid(current_user)
    records = _parse_csv(raw)
    for r in records:
        r["workspace_id"] = wid

    db = get_db()
    # Replace previous CSV/demo data completely and re-run detectors.
    await db.financial_records.delete_many({"workspace_id": wid})
    await db.signals.delete_many({"workspace_id": wid})
    await db.financial_records.insert_many(records)

    signals = run_all_detectors(records)
    id_to_r = {r["record_id"]: r for r in records}
    now = datetime.now(timezone.utc).isoformat()
    signal_docs = []
    for s in signals:
        ev = [id_to_r[rid] for rid in s["evidence_record_ids"] if rid in id_to_r]
        fb = _fallback_explanation(s, ev)
        signal_docs.append({
            "signal_id": f"sig_{uuid.uuid4().hex[:12]}",
            "workspace_id": wid,
            **s,
            "explanation": fb["explanation"],
            "recommended_action": fb["recommended_action"],
            "status": "open",
            "generated_by": "rule",
            "ai_enriched": False,
            "created_at": now,
            "resolved_at": None,
        })
    if signal_docs:
        await db.signals.insert_many(signal_docs)

    await db.workspaces.update_one(
        {"workspace_id": wid},
        {"$set": {
            "is_seeded": True,
            "data_source": "csv",
            "last_import_at": now,
        }},
    )
    return {
        "ok": True,
        "imported_records": len(records),
        "generated_signals": len(signal_docs),
    }
