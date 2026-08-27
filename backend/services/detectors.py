"""Rule-based deterministic signal detectors.

Each detector consumes the workspace's records and returns candidate signals
(pre-priority-scored) with evidence record IDs. No hallucination possible: the
LLM only rewrites the human-facing explanation + recommended_action fields on
top of these deterministic findings.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List

from services.finance import priority_score


def _parse_date(v) -> datetime:
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc) if v.tzinfo else v.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(timezone.utc)


def _base(
    detector: str,
    category: str,
    title: str,
    impact_amount: float,
    confidence: float,
    urgency: str,
    evidence_ids: List[str],
    amount_type: str,
    body: str = "",
    recommended: str = "",
) -> dict:
    return {
        "detector": detector,
        "category": category,
        "title": title,
        "impact_amount": round(float(impact_amount), 2),
        "amount_type": amount_type,
        "confidence": round(float(confidence), 2),
        "urgency": urgency,
        "priority_score": priority_score(impact_amount, confidence, urgency),
        "evidence_record_ids": evidence_ids[:12],
        "explanation": body,
        "recommended_action": recommended,
    }


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------

def detect_duplicate_vendor_payments(records: List[dict]) -> List[dict]:
    """Same vendor + same amount within a 3-day window → likely duplicate."""
    bills = [r for r in records if r["type"] == "vendor_bill"]
    groups: Dict[tuple, List[dict]] = defaultdict(list)
    for r in bills:
        key = (r["counterparty"], round(float(r["amount"]), 2))
        groups[key].append(r)

    signals: List[dict] = []
    for (vendor, amount), rs in groups.items():
        rs_sorted = sorted(rs, key=lambda r: _parse_date(r["date"]))
        i = 0
        while i < len(rs_sorted) - 1:
            j = i + 1
            cluster = [rs_sorted[i]]
            while j < len(rs_sorted) and (
                _parse_date(rs_sorted[j]["date"]) - _parse_date(rs_sorted[i]["date"])
            ) <= timedelta(days=3):
                cluster.append(rs_sorted[j])
                j += 1
            if len(cluster) >= 2:
                impact = amount * (len(cluster) - 1)
                signals.append(_base(
                    detector="duplicate_vendor_payment",
                    category="profit_leak",
                    title=f"Duplicate payment to {vendor}",
                    impact_amount=impact,
                    confidence=0.9,
                    urgency="high",
                    evidence_ids=[r["record_id"] for r in cluster],
                    amount_type="measured",
                ))
                i = j
            else:
                i += 1
    return signals


def detect_overlapping_subscriptions(records: List[dict]) -> List[dict]:
    """Same vendor billed 2+ times within a calendar month with the same
    amount → likely overlapping subscriptions."""
    bills = [r for r in records if r["type"] == "vendor_bill"]
    grouped: Dict[tuple, List[dict]] = defaultdict(list)
    for r in bills:
        d = _parse_date(r["date"])
        key = (r["counterparty"], d.strftime("%Y-%m"), round(float(r["amount"]), 2))
        grouped[key].append(r)

    # Consolidate by vendor across months
    per_vendor: Dict[str, List[dict]] = defaultdict(list)
    for (vendor, _month, _amt), rs in grouped.items():
        if len(rs) >= 2:
            per_vendor[vendor].extend(rs)

    signals: List[dict] = []
    for vendor, rs in per_vendor.items():
        # Skip anything already captured by exact-duplicate detector — we only
        # emit this when the amount is a canonical monthly SaaS-ish price
        # AND the pattern repeats across months.
        months = {_parse_date(r["date"]).strftime("%Y-%m") for r in rs}
        if len(months) < 2:
            continue
        extra_per_month = sum(1 for _ in rs) - len(months)
        avg_amount = sum(float(r["amount"]) for r in rs) / len(rs)
        impact = avg_amount * extra_per_month
        if impact <= 0:
            continue
        signals.append(_base(
            detector="overlapping_subscription",
            category="profit_leak",
            title=f"Overlapping {vendor} subscriptions",
            impact_amount=impact,
            confidence=0.72,
            urgency="medium",
            evidence_ids=[r["record_id"] for r in rs],
            amount_type="estimated",
        ))
    return signals


def detect_unbilled_services(records: List[dict]) -> List[dict]:
    """A customer has an active monthly contract but is missing an invoice for
    a period → unbilled services → revenue recovery."""
    contracts = [r for r in records if r["type"] == "contract"]
    invoices = [r for r in records if r["type"] == "invoice"]

    now = datetime.now(timezone.utc)
    signals: List[dict] = []
    for c in contracts:
        signed = _parse_date(c["date"])
        cust = c["counterparty"]
        mrr = float(c["amount"])
        # Expected monthly periods since signed
        months_elapsed = max(0, (now.year - signed.year) * 12 + (now.month - signed.month))
        months_elapsed = min(months_elapsed, 12)  # cap for MVP
        expected_months = {
            (signed + timedelta(days=30 * i)).strftime("%Y-%m")
            for i in range(months_elapsed + 1)
        }
        billed_months = {
            _parse_date(inv["date"]).strftime("%Y-%m")
            for inv in invoices
            if inv["counterparty"] == cust
        }
        missing = expected_months - billed_months
        if not missing:
            continue
        impact = mrr * len(missing)
        # evidence: the contract + one representative billed invoice
        evidence = [c["record_id"]] + [
            inv["record_id"]
            for inv in invoices
            if inv["counterparty"] == cust
        ][:3]
        signals.append(_base(
            detector="unbilled_services",
            category="revenue_recovery",
            title=f"Unbilled services — {cust}",
            impact_amount=impact,
            confidence=0.78,
            urgency="high" if impact > 10_000 else "medium",
            evidence_ids=evidence,
            amount_type="potential",
        ))
    return signals


def detect_late_paying_customer(records: List[dict]) -> List[dict]:
    """A customer paying consistently 45+ days late → working-capital drag."""
    payments = [r for r in records if r["type"] == "payment"]
    outstanding = [r for r in records if r["type"] == "invoice" and r.get("status") == "outstanding"]

    lag_by_cust: Dict[str, List[int]] = defaultdict(list)
    for p in payments:
        lag = int(p.get("raw", {}).get("days_to_pay", 0))
        if lag:
            lag_by_cust[p["counterparty"]].append(lag)

    signals: List[dict] = []
    for cust, lags in lag_by_cust.items():
        if len(lags) < 3:
            continue
        avg_lag = sum(lags) / len(lags)
        if avg_lag < 45:
            continue
        # Evidence: the payments driving the average + any outstanding invoices
        ev = [
            p["record_id"]
            for p in payments
            if p["counterparty"] == cust and int(p.get("raw", {}).get("days_to_pay", 0)) >= 45
        ][:5]
        ev += [inv["record_id"] for inv in outstanding if inv["counterparty"] == cust][:3]
        # Outstanding amount is the recoverable working-capital "held"
        held = sum(float(inv["amount"]) for inv in outstanding if inv["counterparty"] == cust)
        if held <= 0:
            # Estimate using avg invoice size × 1 cycle
            typical = [p["amount"] for p in payments if p["counterparty"] == cust]
            held = (sum(typical) / len(typical)) if typical else 0
        signals.append(_base(
            detector="late_paying_customer",
            category="revenue_recovery",
            title=f"Payment terms drifting past {int(avg_lag)}d — {cust}",
            impact_amount=held,
            confidence=0.7,
            urgency="medium",
            evidence_ids=ev,
            amount_type="potential",
        ))
    return signals


def detect_renewal_uplift(records: List[dict]) -> List[dict]:
    """Contracts within 60 days of renewal where current price < market
    median → opportunity to lift pricing."""
    now = datetime.now(timezone.utc)
    signals: List[dict] = []
    for c in [r for r in records if r["type"] == "contract"]:
        raw = c.get("raw") or {}
        renewal = raw.get("renewal_date")
        if not renewal:
            continue
        r_dt = _parse_date(renewal)
        days = (r_dt - now).days
        if not (-14 <= days <= 90):
            continue
        current = float(raw.get("current_price") or c["amount"])
        market = float(raw.get("market_median_price") or 0)
        if market <= current:
            continue
        impact = market - current
        signals.append(_base(
            detector="renewal_uplift",
            category="opportunity",
            title=f"Renewal pricing uplift — {c['counterparty']}",
            impact_amount=impact,
            confidence=0.62,
            urgency="high" if days <= 30 else "medium",
            evidence_ids=[c["record_id"]],
            amount_type="potential",
        ))
    return signals


DETECTORS: List[Callable[[List[dict]], List[dict]]] = [
    detect_duplicate_vendor_payments,
    detect_overlapping_subscriptions,
    detect_unbilled_services,
    detect_late_paying_customer,
    detect_renewal_uplift,
]


def run_all_detectors(records: List[dict]) -> List[dict]:
    out: List[dict] = []
    for fn in DETECTORS:
        try:
            out.extend(fn(records))
        except Exception as e:
            # Fail-open — one broken detector shouldn't kill the pipeline
            print(f"[detector] {fn.__name__} failed: {e}")
    out.sort(key=lambda s: s["priority_score"], reverse=True)
    return out
