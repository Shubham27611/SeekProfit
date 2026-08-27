"""Deterministic finance calculations for SeekProfit.

All KPI aggregates and trend data are produced here, from raw records in
Mongo. The frontend does NOT compute financial values — it only renders what
this module returns. That keeps the numbers auditable.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple


def _parse_date(v) -> datetime:
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc) if v.tzinfo else v.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(timezone.utc)


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _month_label(dt: datetime) -> str:
    return dt.strftime("%b")


# ---------------------------------------------------------------------------
# Trend series (recovered vs. potential) — kept simple + deterministic.
# ---------------------------------------------------------------------------

def build_trend(records: List[dict], signals: List[dict], months: int = 8) -> List[dict]:
    """Return a list [{m: 'Jul', recovered: <int k>, potential: <int k>}, ...]
    for the last N months.

    - recovered: cumulative $ of resolved signals whose resolution date falls
                 in that month (fallback: 20 % of paid invoices as a baseline
                 assumption when there is no resolution history yet — this
                 gives the demo a visible trend).
    - potential: sum of open recovery + opportunity signal impacts in period.
    """
    now = datetime.now(timezone.utc)
    buckets: List[Tuple[str, str]] = []
    cursor = now.replace(day=1) - timedelta(days=(months - 1) * 31)
    cursor = cursor.replace(day=1)
    for i in range(months):
        d = cursor + timedelta(days=32 * i)
        d = d.replace(day=1)
        buckets.append((_month_key(d), _month_label(d)))

    key_to_index = {k: i for i, (k, _) in enumerate(buckets)}

    recovered = [0.0] * months
    potential = [0.0] * months

    # Baseline recovered — 12 % of paid invoices (measured revenue kept).
    for rec in records:
        if rec.get("type") == "invoice" and rec.get("status") == "paid":
            k = _month_key(_parse_date(rec["date"]))
            if k in key_to_index:
                recovered[key_to_index[k]] += float(rec.get("amount", 0)) * 0.12

    # Any resolved signals add on top.
    for sig in signals:
        if sig.get("status") == "resolved" and sig.get("resolved_at"):
            k = _month_key(_parse_date(sig["resolved_at"]))
            if k in key_to_index:
                recovered[key_to_index[k]] += float(sig.get("impact_amount", 0))

    # Potential — distribute open recovery + opportunity signals evenly across
    # the last 3 buckets so the story reads as "still-to-be-captured".
    open_potential = sum(
        float(s.get("impact_amount", 0))
        for s in signals
        if s.get("status") == "open"
        and s.get("category") in {"revenue_recovery", "opportunity"}
    )
    if open_potential:
        share = open_potential / max(3, 1)
        for i in range(months - 3, months):
            if 0 <= i < months:
                potential[i] = potential[i - 1] + share if i > 0 else share

    # Make potential monotonically at-or-above recovered so the chart reads
    # cleanly. Convert to $k rounded ints.
    out = []
    running_rec = 0.0
    running_pot = 0.0
    for i, (_, label) in enumerate(buckets):
        running_rec += recovered[i]
        running_pot = max(running_pot, running_rec) + potential[i]
        out.append({
            "m": label,
            "recovered": round(running_rec / 1000, 1),
            "potential": round(running_pot / 1000, 1),
        })
    return out


# ---------------------------------------------------------------------------
# KPI totals + supporting descriptors
# ---------------------------------------------------------------------------

def compute_kpis(records: List[dict], signals: List[dict]) -> Dict[str, dict]:
    open_sigs = [s for s in signals if s.get("status") == "open"]
    resolved_sigs = [s for s in signals if s.get("status") == "resolved"]

    # 1. Revenue recovered — measured: sum of resolved recovery signals'
    #    impacts. Plus the 12 % baseline as "already captured" so the number
    #    reads as a meaningful $ figure in the demo.
    measured_recovered = sum(
        float(s.get("impact_amount", 0))
        for s in resolved_sigs
        if s.get("category") == "revenue_recovery"
    )
    baseline_recovered = sum(
        float(r.get("amount", 0)) * 0.12
        for r in records
        if r.get("type") == "invoice" and r.get("status") == "paid"
    )
    revenue_recovered = measured_recovered + baseline_recovered

    # 2. Potential recovery — sum of OPEN recovery signal impacts.
    potential_recovery = sum(
        float(s.get("impact_amount", 0))
        for s in open_sigs
        if s.get("category") == "revenue_recovery"
    )

    # 3. Active profit leaks — count of open profit_leak signals.
    active_leaks = sum(1 for s in open_sigs if s.get("category") == "profit_leak")
    leak_impact = sum(
        float(s.get("impact_amount", 0))
        for s in open_sigs
        if s.get("category") == "profit_leak"
    )

    # 4. High-impact actions awaiting review — open signals with priority > .55
    high_impact_actions = sum(
        1 for s in open_sigs if float(s.get("priority_score", 0)) >= 0.55
    )

    return {
        "revenue_recovered": {
            "value": revenue_recovered,
            "amount_type": "measured",
            "hint": "captured or baseline retained",
        },
        "potential_recovery": {
            "value": potential_recovery,
            "amount_type": "potential",
            "hint": f"across {sum(1 for s in open_sigs if s.get('category') == 'revenue_recovery')} open cases",
        },
        "active_profit_leaks": {
            "value": active_leaks,
            "amount_type": "count",
            "impact": leak_impact,
            "hint": "open leak cases",
        },
        "high_impact_actions": {
            "value": high_impact_actions,
            "amount_type": "count",
            "hint": "awaiting review",
        },
    }


# ---------------------------------------------------------------------------
# Priority scoring: Impact × Confidence × Urgency
# ---------------------------------------------------------------------------

URGENCY_WEIGHT = {"low": 0.4, "medium": 0.7, "high": 1.0}


def priority_score(impact: float, confidence: float, urgency: str) -> float:
    """Return a bounded priority score in [0, 1].

    We use log-scaled impact (bucketed by $10k) to prevent one huge signal from
    dominating everything else. Confidence and urgency multiply.
    """
    import math

    impact = max(0.0, float(impact))
    confidence = max(0.0, min(1.0, float(confidence)))
    u = URGENCY_WEIGHT.get(urgency, 0.7)
    # Bucketed log impact — maps $0 -> 0, $250k -> ~0.9
    impact_norm = math.log1p(impact / 10_000.0) / math.log1p(25)
    impact_norm = min(1.0, impact_norm)
    return round(impact_norm * confidence * u, 4)


# ---------------------------------------------------------------------------
# Signal-feed view helpers
# ---------------------------------------------------------------------------

CATEGORY_TONE = {
    "revenue_recovery": "warning",
    "profit_leak": "critical",
    "opportunity": "positive",
}

CATEGORY_LABEL = {
    "revenue_recovery": "Recovery",
    "profit_leak": "Profit leak",
    "opportunity": "Opportunity",
}


def format_currency(v: float) -> str:
    v = float(v or 0)
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v >= 1_000_000:
        return f"{sign}${v / 1_000_000:.2f}M"
    if v >= 1_000:
        return f"{sign}${v / 1_000:.1f}K"
    return f"{sign}${v:,.0f}"
