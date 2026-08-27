"""Executive report — a board-ready aggregated brief of the workspace."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from core.db import get_db
from core.security import get_current_user
from services.finance import (
    compute_kpis,
    build_trend,
    format_currency,
    CATEGORY_LABEL,
    CATEGORY_TONE,
)


router = APIRouter(prefix="/api/reports", tags=["reports"])


async def _workspace(user: dict) -> dict:
    db = get_db()
    ws = await db.workspaces.find_one(
        {"$or": [
            {"owner_user_id": user["user_id"]},
            {"invited_emails": user["email"]},
        ]},
        {"_id": 0},
    )
    if not ws:
        raise HTTPException(status_code=404, detail="No workspace.")
    return ws


def _category_totals(signals: List[dict]) -> dict:
    totals = defaultdict(lambda: {"open_count": 0, "open_impact": 0.0, "resolved_impact": 0.0})
    for s in signals:
        cat = s.get("category")
        if s.get("status") == "open":
            totals[cat]["open_count"] += 1
            totals[cat]["open_impact"] += float(s.get("impact_amount", 0))
        elif s.get("status") == "resolved":
            totals[cat]["resolved_impact"] += float(s.get("impact_amount", 0))
    return {
        cat: {
            "category": cat,
            "label": CATEGORY_LABEL.get(cat, cat),
            "tone": CATEGORY_TONE.get(cat, "warning"),
            "open_count": v["open_count"],
            "open_impact": v["open_impact"],
            "open_impact_display": format_currency(v["open_impact"]),
            "resolved_impact": v["resolved_impact"],
            "resolved_impact_display": format_currency(v["resolved_impact"]),
        }
        for cat, v in totals.items()
    }


def _top_counterparties(records: List[dict], top_n: int = 5) -> List[dict]:
    by_cust = defaultdict(lambda: {"invoiced": 0.0, "paid": 0.0, "outstanding": 0.0, "count": 0})
    by_vendor = defaultdict(lambda: {"spend": 0.0, "count": 0})
    for r in records:
        t = r.get("type")
        amt = float(r.get("amount", 0))
        cp = r.get("counterparty") or "Unknown"
        if t == "invoice":
            by_cust[cp]["invoiced"] += amt
            by_cust[cp]["count"] += 1
            if r.get("status") == "outstanding":
                by_cust[cp]["outstanding"] += amt
        elif t == "payment":
            by_cust[cp]["paid"] += amt
        elif t == "vendor_bill":
            by_vendor[cp]["spend"] += amt
            by_vendor[cp]["count"] += 1

    customers = sorted(
        [{"name": k, **v, "invoiced_display": format_currency(v["invoiced"]), "outstanding_display": format_currency(v["outstanding"])} for k, v in by_cust.items()],
        key=lambda x: x["invoiced"],
        reverse=True,
    )[:top_n]
    vendors = sorted(
        [{"name": k, **v, "spend_display": format_currency(v["spend"])} for k, v in by_vendor.items()],
        key=lambda x: x["spend"],
        reverse=True,
    )[:top_n]
    return {"customers": customers, "vendors": vendors}


@router.get("/executive")
async def executive_report(current_user: dict = Depends(get_current_user)):
    db = get_db()
    ws = await _workspace(current_user)
    wid = ws["workspace_id"]
    records = await db.financial_records.find({"workspace_id": wid}, {"_id": 0}).to_list(5000)
    signals = await db.signals.find({"workspace_id": wid}, {"_id": 0}).to_list(500)

    kpis = compute_kpis(records, signals)
    trend = build_trend(records, signals)
    cat_totals = _category_totals(signals)
    top_cp = _top_counterparties(records)

    open_signals = sorted(
        [s for s in signals if s.get("status") == "open"],
        key=lambda s: float(s.get("priority_score", 0)),
        reverse=True,
    )
    resolved_signals = [s for s in signals if s.get("status") == "resolved"]

    top_actions = [
        {
            "signal_id": s["signal_id"],
            "title": s["title"],
            "category": s["category"],
            "category_label": CATEGORY_LABEL.get(s["category"], s["category"]),
            "tone": CATEGORY_TONE.get(s["category"], "warning"),
            "impact_amount": s.get("impact_amount", 0),
            "impact_display": format_currency(s.get("impact_amount", 0)),
            "amount_type": s.get("amount_type"),
            "confidence": s.get("confidence"),
            "urgency": s.get("urgency"),
            "owner_email": s.get("owner_email"),
            "due_date": s.get("due_date"),
            "recommended_action": s.get("recommended_action"),
        }
        for s in open_signals[:8]
    ]

    return {
        "workspace": {
            "name": ws.get("name"),
            "industry": ws.get("industry"),
            "currency": ws.get("currency", "USD"),
            "data_source": ws.get("data_source"),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_label": "Last 8 months",
        "headline": {
            "revenue_recovered_display": format_currency(kpis["revenue_recovered"]["value"]),
            "revenue_recovered_amount": kpis["revenue_recovered"]["value"],
            "open_pipeline_display": format_currency(
                sum(v["open_impact"] for v in cat_totals.values())
            ),
            "open_pipeline_amount": sum(v["open_impact"] for v in cat_totals.values()),
            "open_signal_count": sum(v["open_count"] for v in cat_totals.values()),
            "records_analyzed": len(records),
        },
        "category_totals": list(cat_totals.values()),
        "trend": trend,
        "top_actions": top_actions,
        "top_counterparties": top_cp,
        "resolved_wins": [
            {
                "signal_id": s["signal_id"],
                "title": s["title"],
                "category_label": CATEGORY_LABEL.get(s["category"], s["category"]),
                "impact_display": format_currency(s.get("impact_amount", 0)),
                "resolved_at": s.get("resolved_at"),
            }
            for s in sorted(
                resolved_signals,
                key=lambda s: s.get("resolved_at") or "",
                reverse=True,
            )[:6]
        ],
    }
