"""Probe: which resolved signal categories move the Revenue Recovered KPI?"""
import json
import uuid

import requests
from conftest import BASE_URL, auth_session

from test_grounding_kpi_only import _new_inr_workspace  # noqa: E402


def main():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    c = _new_inr_workspace(s, "probe_cat")
    sigs = c.get(f"{BASE_URL}/api/signals?limit=50", timeout=60).json()["signals"]
    print("signals:")
    for x in sigs:
        print(f"  {x['category']:<16} {x['detector']:<28} {x['impact_amount']:>10} {x['title']}")

    def snapshot(tag):
        ov = c.get(f"{BASE_URL}/api/overview", timeout=60).json()
        rep = c.get(f"{BASE_URL}/api/reports/executive", timeout=90).json()
        rec = [k for k in ov["kpis"] if k["slug"] == "recovered"][0]
        print(f"[{tag}] overview recovered={rec['value_display']} hint={rec['hint']!r} "
              f"| report amount={rep['headline']['revenue_recovered_amount']} "
              f"| trend recovered={[t['recovered'] for t in rep['trend']]}")

    snapshot("baseline")

    dup = [x for x in sigs if x["detector"] == "duplicate_vendor_payment"
           and float(x["impact_amount"]) == 46000.0][0]
    r = c.post(f"{BASE_URL}/api/signals/{dup['signal_id']}/status",
               json={"status": "resolved"}, timeout=60)
    print("resolve duplicate(profit_leak) ->", r.status_code)
    snapshot("after resolving profit_leak duplicate 46000")

    rr = [x for x in sigs if x["category"] == "revenue_recovery"]
    if rr:
        t = rr[0]
        r = c.post(f"{BASE_URL}/api/signals/{t['signal_id']}/status",
                   json={"status": "resolved"}, timeout=60)
        print(f"resolve revenue_recovery {t['impact_amount']} ->", r.status_code)
        snapshot(f"after resolving revenue_recovery {t['impact_amount']}")
    else:
        print("no revenue_recovery signals in this dataset")


main()
