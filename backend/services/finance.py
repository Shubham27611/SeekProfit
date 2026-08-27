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

# Signals in these categories represent CASH that was actually recovered or
# prevented when marked resolved. Duplicate-payment reversals live under
# 'profit_leak' but resolving one recovers real cash, so they count too.
RECOVERY_ELIGIBLE_CATEGORIES: set = {"revenue_recovery", "profit_leak"}


def _month_step(dt: datetime, delta_months: int) -> datetime:
    """Return a datetime shifted by `delta_months` calendar months (day=1)."""
    total = dt.year * 12 + (dt.month - 1) + delta_months
    year, month = divmod(total, 12)
    return dt.replace(year=year, month=month + 1, day=1)


def build_trend(records: List[dict], signals: List[dict], months: int = 8) -> List[dict]:
    """Return a list [{m: 'Jul', recovered: <n k>, potential: <n k>}, ...]
    for the last N months INCLUDING the current month.

    - recovered: cumulative resolved-signal impacts (recovery-eligible only)
                 whose resolution date falls in that bucket.
    - potential: sum of open recovery + opportunity signal impacts spread
                 across the last three buckets.
    """
    now = datetime.now(timezone.utc)
    # Anchor on the first day of the current month, then walk back N-1 months.
    end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    buckets: List[Tuple[str, str]] = []
    for i in range(months - 1, -1, -1):
        d = _month_step(end, -i)
        buckets.append((_month_key(d), _month_label(d)))

    key_to_index = {k: i for i, (k, _) in enumerate(buckets)}

    recovered = [0.0] * months
    potential = [0.0] * months

    for sig in signals:
        if (
            sig.get("status") == "resolved"
            and sig.get("resolved_at")
            and sig.get("category") in RECOVERY_ELIGIBLE_CATEGORIES
        ):
            k = _month_key(_parse_date(sig["resolved_at"]))
            if k in key_to_index:
                recovered[key_to_index[k]] += float(sig.get("impact_amount", 0))

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

    # 1. Revenue recovered — MEASURED ONLY: sum of impacts from RESOLVED signals
    #    in the recovery-eligible categories (revenue_recovery + profit_leak).
    #    A resolved duplicate-payment reversal recovers real cash and counts.
    contributing = [
        s for s in resolved_sigs
        if s.get("category") in RECOVERY_ELIGIBLE_CATEGORIES
    ]
    revenue_recovered = sum(float(s.get("impact_amount", 0)) for s in contributing)

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

    hint_recovered = (
        f"across {len(contributing)} resolved case{'s' if len(contributing) != 1 else ''}"
        if revenue_recovered > 0
        else "no prior recovery in this dataset"
    )

    return {
        "revenue_recovered": {
            "value": revenue_recovered,
            "amount_type": "measured",
            "hint": hint_recovered,
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


CURRENCY_SYMBOLS: Dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "INR": "₹",
    "JPY": "¥",
    "CNY": "¥",
    "CAD": "$",
    "AUD": "$",
    "SGD": "$",
    "AED": "د.إ",
    "CHF": "CHF ",
}


def currency_symbol(code: str) -> str:
    return CURRENCY_SYMBOLS.get((code or "USD").upper(), (code or "").upper() + " ")


def format_currency(v: float, currency: str = "USD") -> str:
    """Format an amount with the correct currency symbol.

    Full magnitudes are formatted as `<sym><n,nnn>` (e.g. ₹27,500). Amounts
    over 1,000 are abbreviated as K/M so the UI keeps its density
    (e.g. ₹27.5K, $1.24M)."""
    sym = currency_symbol(currency)
    v = float(v or 0)
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v >= 1_000_000:
        return f"{sign}{sym}{v / 1_000_000:.2f}M"
    if v >= 1_000:
        return f"{sign}{sym}{v / 1_000:.1f}K"
    return f"{sign}{sym}{v:,.0f}"


def format_amount_exact(v: float, currency: str = "USD") -> str:
    """Full-precision variant (no K/M abbreviation) — used inside AI answers
    and citations where the LLM is expected to name real numbers."""
    sym = currency_symbol(currency)
    v = float(v or 0)
    sign = "-" if v < 0 else ""
    v = abs(v)
    return f"{sign}{sym}{v:,.0f}"
