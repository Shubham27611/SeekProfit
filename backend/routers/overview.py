"""Overview KPI + trend + signal-feed API."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException

from core.db import get_db
from core.security import get_current_user
from services.finance import (
    build_trend,
    compute_kpis,
    CATEGORY_LABEL,
    CATEGORY_TONE,
    format_currency,
)


router = APIRouter(prefix="/api/overview", tags=["overview"])


async def _get_workspace(user: dict):
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


@router.get("")
async def get_overview(current_user: dict = Depends(get_current_user)):
    db = get_db()
    ws = await _get_workspace(current_user)
    wid = ws["workspace_id"]

    records = await db.financial_records.find({"workspace_id": wid}, {"_id": 0}).to_list(5000)
    signals = await db.signals.find({"workspace_id": wid}, {"_id": 0}).to_list(500)

    kpis = compute_kpis(records, signals)
    trend = build_trend(records, signals)

    # Signal feed — top 6 open by priority
    open_signals = sorted(
        [s for s in signals if s.get("status") == "open"],
        key=lambda s: float(s.get("priority_score", 0)),
        reverse=True,
    )[:6]
    feed = [
        {
            "id": s["signal_id"],
            "title": s["title"],
            "source": _source_label(s),
            "amount_display": format_currency(s.get("impact_amount", 0)),
            "amount_type": s.get("amount_type"),
            "tone": CATEGORY_TONE.get(s["category"], "warning"),
            "badge": CATEGORY_LABEL.get(s["category"], s["category"]),
            "priority_score": s.get("priority_score", 0),
        }
        for s in open_signals
    ]

    # Formatted KPI display values
    kpi_display = _format_kpis(kpis)

    return {
        "workspace": {
            "workspace_id": ws["workspace_id"],
            "name": ws.get("name"),
            "is_seeded": bool(ws.get("is_seeded")),
            "data_source": ws.get("data_source"),
            "currency": ws.get("currency", "USD"),
        },
        "kpis": kpi_display,
        "trend": trend,
        "feed": feed,
        "counts": {
            "records": len(records),
            "signals_open": sum(1 for s in signals if s.get("status") == "open"),
            "signals_total": len(signals),
        },
    }


def _source_label(signal: dict) -> str:
    detector_map = {
        "duplicate_vendor_payment": "AP Ledger",
        "overlapping_subscription": "Vendor bills",
        "unbilled_services": "Client billing",
        "late_paying_customer": "AR aging",
        "renewal_uplift": "Sales ops",
    }
    return detector_map.get(signal.get("detector", ""), "SeekProfit engine")


def _format_kpis(k: dict) -> list:
    """Frontend-ready KPI cards."""
    return [
        {
            "slug": "recovered",
            "label": "Revenue Recovered",
            "value_display": format_currency(k["revenue_recovered"]["value"]),
            "amount_type": "measured",
            "hint": k["revenue_recovered"]["hint"],
        },
        {
            "slug": "potential",
            "label": "Potential Recovery",
            "value_display": format_currency(k["potential_recovery"]["value"]),
            "amount_type": "potential",
            "hint": k["potential_recovery"]["hint"],
        },
        {
            "slug": "leaks",
            "label": "Active Profit Leaks",
            "value_display": str(k["active_profit_leaks"]["value"]),
            "amount_type": "count",
            "hint": k["active_profit_leaks"]["hint"],
            "supporting_amount": format_currency(k["active_profit_leaks"]["impact"]),
        },
        {
            "slug": "actions",
            "label": "High-Impact Actions",
            "value_display": str(k["high_impact_actions"]["value"]),
            "amount_type": "count",
            "hint": k["high_impact_actions"]["hint"],
        },
    ]
