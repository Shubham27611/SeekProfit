"""Deterministic demo dataset generator.

Every record is tagged `source="demo"` so it can be identified in the UI and
purged when a user imports their own CSV. The generator is deterministic
(seeded RNG) so the same workspace always seeds the same story — which lets
detectors reliably surface the pre-baked leaks + opportunities.
"""
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List


DEMO_VENDORS = [
    "Nimbus Cloud", "AtlasWire", "Northbeam", "Sable Legal", "Halyard Ads",
    "Corvid Studios", "Beacon Freight", "Fern & Copper", "Palladium HR",
    "Sundeck Media",
]
DEMO_CUSTOMERS = [
    "Arclight Robotics", "Meridian Foods", "Kestrel Health", "Union Bay Group",
    "Havenport Logistics", "Iolite Studios", "Northfield Bio", "Prairie Rail",
    "Sable & Vine", "Redshore Ventures", "Anvil Metals", "Copperline Cafe",
]


def _rid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def build_demo_records(workspace_id: str, seed: int = 42) -> List[dict]:
    """Generate ~220 records covering 8 months. Contains intentional anomalies
    so detectors can surface signals with real evidence.
    """
    rng = random.Random(seed)
    now = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    start = now - timedelta(days=240)

    records: List[dict] = []

    def add(rec: dict):
        rec.setdefault("record_id", _rid(rec["type"][:3]))
        rec["workspace_id"] = workspace_id
        rec["source"] = "demo"
        records.append(rec)

    # --- Contracts (recurring revenue) ------------------------------------
    contract_defs = [
        ("Arclight Robotics", 14800, 24, "annual"),
        ("Meridian Foods", 9200, 18, "annual"),
        ("Kestrel Health", 21500, 30, "annual"),
        ("Union Bay Group", 6400, 12, "annual"),
        ("Havenport Logistics", 11200, 24, "annual"),
        ("Iolite Studios", 4800, 12, "monthly"),
        ("Northfield Bio", 17600, 18, "annual"),
    ]
    for cust, mrr, months_active, cadence in contract_defs:
        signed = start + timedelta(days=rng.randint(0, 45))
        add({
            "type": "contract",
            "date": _iso(signed),
            "amount": float(mrr),
            "currency": "USD",
            "counterparty": cust,
            "memo": f"{cadence.title()} contract — MRR baseline",
            "status": "active",
            "raw": {
                "cadence": cadence,
                "months_active": months_active,
                "renewal_date": _iso(signed + timedelta(days=365)),
            },
        })

    # --- Invoices — mostly clean, with intentional gaps -------------------
    # Baseline monthly invoices for each contract customer
    for cust, mrr, months_active, cadence in contract_defs:
        signed = start + timedelta(days=rng.randint(0, 45))
        n_months = 8
        # LEAK: Skip a month for "Meridian Foods" -> unbilled services
        skipped_month = 4 if cust == "Meridian Foods" else -1
        for m in range(n_months):
            if m == skipped_month:
                continue  # intentionally missing
            invoice_date = signed + timedelta(days=30 * m + rng.randint(-3, 3))
            if invoice_date > now:
                continue
            add({
                "type": "invoice",
                "date": _iso(invoice_date),
                "amount": float(mrr) + rng.randint(-40, 40),
                "currency": "USD",
                "counterparty": cust,
                "memo": f"Invoice — {invoice_date.strftime('%b %Y')}",
                "status": "paid" if rng.random() > 0.15 else "outstanding",
                "raw": {"period_month": invoice_date.strftime("%Y-%m")},
            })

    # LEAK: Payment-term drift — a customer paying 45+ days late repeatedly
    late_cust = "Prairie Rail"
    for m in range(6):
        inv_date = now - timedelta(days=210 - m * 30)
        add({
            "type": "invoice",
            "date": _iso(inv_date),
            "amount": 8400.0 + rng.randint(-100, 100),
            "currency": "USD",
            "counterparty": late_cust,
            "memo": f"Invoice — {inv_date.strftime('%b %Y')}",
            "status": "paid" if m < 4 else "outstanding",
            "raw": {"terms_days": 30, "period_month": inv_date.strftime("%Y-%m")},
        })

    # --- Payments (customer) — align with paid invoices --------------------
    for inv in [r for r in records if r["type"] == "invoice" and r["status"] == "paid"]:
        pay_lag = rng.randint(2, 22)
        # For the late-paying customer, deliberately extend the lag
        if inv["counterparty"] == late_cust:
            pay_lag = rng.randint(52, 71)
        pay_date = datetime.fromisoformat(inv["date"]) + timedelta(days=pay_lag)
        if pay_date > now:
            continue
        add({
            "type": "payment",
            "date": _iso(pay_date),
            "amount": inv["amount"],
            "currency": "USD",
            "counterparty": inv["counterparty"],
            "memo": f"Payment against {inv['record_id']}",
            "status": "cleared",
            "raw": {
                "invoice_id": inv["record_id"],
                "days_to_pay": pay_lag,
            },
        })

    # --- Vendor bills — mostly clean, plus LEAKS --------------------------
    for _ in range(70):
        v = rng.choice(DEMO_VENDORS)
        d = start + timedelta(days=rng.randint(0, 235))
        add({
            "type": "vendor_bill",
            "date": _iso(d),
            "amount": round(rng.uniform(180, 6200), 2),
            "currency": "USD",
            "counterparty": v,
            "memo": f"Bill from {v}",
            "status": "paid",
            "raw": {},
        })

    # LEAK: Two obvious duplicate vendor payments (same vendor + amount within 3 days)
    dup_date = now - timedelta(days=32)
    for _ in range(2):
        add({
            "type": "vendor_bill",
            "date": _iso(dup_date + timedelta(days=rng.randint(0, 2))),
            "amount": 4820.00,
            "currency": "USD",
            "counterparty": "AtlasWire",
            "memo": "Invoice AW-49221",
            "status": "paid",
            "raw": {"potential_duplicate": True},
        })
    dup_date_2 = now - timedelta(days=71)
    for _ in range(2):
        add({
            "type": "vendor_bill",
            "date": _iso(dup_date_2 + timedelta(days=rng.randint(0, 1))),
            "amount": 1275.00,
            "currency": "USD",
            "counterparty": "Halyard Ads",
            "memo": "Campaign management retainer",
            "status": "paid",
            "raw": {"potential_duplicate": True},
        })

    # LEAK: Overlapping SaaS subscriptions (two "Northbeam" bills same month, same amount)
    for m in range(4):
        base = now - timedelta(days=120 - m * 30)
        for _ in range(2):
            add({
                "type": "vendor_bill",
                "date": _iso(base + timedelta(days=rng.randint(0, 4))),
                "amount": 899.00,
                "currency": "USD",
                "counterparty": "Northbeam",
                "memo": "Attribution platform — monthly seat",
                "status": "paid",
                "raw": {"category": "saas"},
            })

    # OPPORTUNITY: Contracts approaching renewal within 60 days
    add({
        "type": "contract",
        "date": _iso(now - timedelta(days=305)),
        "amount": 16800.0,
        "currency": "USD",
        "counterparty": "Sable & Vine",
        "memo": "Annual retainer — up for renewal",
        "status": "active",
        "raw": {
            "cadence": "annual",
            "months_active": 11,
            "renewal_date": _iso(now + timedelta(days=45)),
            "current_price": 16800.0,
            "market_median_price": 21500.0,
        },
    })
    add({
        "type": "contract",
        "date": _iso(now - timedelta(days=340)),
        "amount": 9800.0,
        "currency": "USD",
        "counterparty": "Redshore Ventures",
        "memo": "Annual license — up for renewal",
        "status": "active",
        "raw": {
            "cadence": "annual",
            "months_active": 11,
            "renewal_date": _iso(now + timedelta(days=25)),
            "current_price": 9800.0,
            "market_median_price": 12250.0,
        },
    })

    return records
