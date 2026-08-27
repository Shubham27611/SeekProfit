"""Diagnose build_trend bucket coverage for a just-resolved signal."""
from datetime import datetime, timezone
import sys
sys.path.insert(0, "/app/backend")
from services.finance import build_trend, _month_key  # noqa: E402

now = datetime.now(timezone.utc)
print("now:", now.isoformat())
sig = [{"status": "resolved", "resolved_at": now.isoformat(),
        "impact_amount": 1100000.0, "category": "revenue_recovery"}]
out = build_trend([], sig)
print("buckets:", [b["m"] for b in out])
print("recovered:", [b["recovered"] for b in out])
print("month key for now:", _month_key(now))
