"""Iteration 6: verify the patch for
 (1) compute_kpis()/build_trend() using RECOVERY_ELIGIBLE_CATEGORIES
     (revenue_recovery + profit_leak),
 (2) build_trend() calendar-month buckets INCLUDING the current month,
 (3) routers/ai.py _scrub_internal_terms() deterministic scrub.
"""
import json
import uuid

import pytest
import requests

from conftest import BASE_URL, auth_session

RUPEE = "\u20b9"

INR_CSV = """type,date,amount,counterparty,memo,status,currency
vendor_bill,2026-01-05,27500,Ad Network India,Q4 campaign management,paid,INR
vendor_bill,2026-01-06,27500,Ad Network India,Q4 campaign management (duplicate?),paid,INR
vendor_bill,2026-01-15,46000,Cloud Vendor,Compute reserved instance,paid,INR
vendor_bill,2026-01-18,46000,Cloud Vendor,Compute reserved instance,paid,INR
invoice,2026-01-10,120000,Acme Retail,Retainer January,paid,INR
payment,2026-01-25,120000,Acme Retail,Retainer January,cleared,INR
contract,2025-08-01,110000,Nova Media,Annual retainer,active,INR
invoice,2025-09-01,110000,Nova Media,September retainer,paid,INR
invoice,2025-10-01,110000,Nova Media,October retainer,paid,INR
"""

LEAK_WORDS = [
    "the brief", "this brief", "the json", "dataset_facts",
    "prior_recovery_available", "top_signals", "sample_records",
]


def _new_inr_workspace(prefix="it6"):
    api = requests.Session()
    api.headers.update({"Content-Type": "application/json"})
    email = f"{prefix}_{uuid.uuid4().hex[:8]}@seekprofit.app"
    r = api.post(f"{BASE_URL}/api/auth/register",
                 json={"email": email, "password": "testpass123", "name": "TEST Iter6 QA"},
                 timeout=30)
    assert r.status_code == 200, f"register failed {r.status_code}: {r.text[:300]}"
    token = r.json()["token"]
    s = auth_session(token)
    s.jwt = token
    s.email = email
    r = s.post(f"{BASE_URL}/api/workspace/setup",
               json={"business_name": "TEST Iter6 Co", "industry": "saas",
                     "currency": "USD", "load_demo_data": False}, timeout=90)
    assert r.status_code == 200, f"setup failed {r.status_code}: {r.text[:300]}"
    up = requests.Session()
    up.headers.update({"Authorization": f"Bearer {token}"})
    r = up.post(f"{BASE_URL}/api/imports/csv",
                files={"file": ("inr.csv", INR_CSV.encode(), "text/csv")}, timeout=120)
    assert r.status_code == 200, f"csv import failed {r.status_code}: {r.text[:400]}"
    body = r.json()
    assert body["currency"] == "INR", body
    assert body["imported_records"] == 9, body
    return s


def _kpi(kpis, slug):
    m = [k for k in kpis if k.get("slug") == slug]
    assert m, f"kpi slug {slug} missing: {[k.get('slug') for k in kpis]}"
    return m[0]


def _signals(c):
    r = c.get(f"{BASE_URL}/api/signals?limit=50", timeout=60)
    assert r.status_code == 200, r.text[:300]
    return r.json()["signals"]


def _resolve(c, sid):
    r = c.post(f"{BASE_URL}/api/signals/{sid}/status",
               json={"status": "resolved"}, timeout=60)
    assert r.status_code == 200, r.text[:300]


def _leaks(text):
    low = text.lower()
    return [w for w in LEAK_WORDS if w in low]


# ---------------------------------------------------------------------------
# SCENARIO A + B — resolving a profit_leak duplicate moves Revenue Recovered,
# and the current-month trend bucket shows it.
# ---------------------------------------------------------------------------
class TestScenarioADuplicateResolutionMovesKPI:
    @pytest.fixture(scope="class")
    def client(self):
        c = _new_inr_workspace("it6_dup")
        sigs = _signals(c)
        target = [s for s in sigs
                  if s.get("category") == "profit_leak"
                  and float(s["impact_amount"]) == 46000.0
                  and "Cloud Vendor" in s["title"]]
        assert target, [(s["title"], s["category"], s["impact_amount"]) for s in sigs]
        _resolve(c, target[0]["signal_id"])
        c.all_signals = sigs
        return c

    def test_overview_recovered_is_46000_rupees(self, client):
        d = client.get(f"{BASE_URL}/api/overview", timeout=60).json()
        assert d["workspace"]["currency"] == "INR", d["workspace"]
        rec = _kpi(d["kpis"], "recovered")
        assert rec["value_display"] in (f"{RUPEE}46,000", f"{RUPEE}46.0K"), rec
        assert rec["amount"] == 46000.0 if "amount" in rec else True
        hint = (rec.get("hint") or "").lower()
        assert "no prior recovery" not in hint, rec
        assert "1 resolved case" in hint, rec

    def test_executive_revenue_recovered_amount(self, client):
        d = client.get(f"{BASE_URL}/api/reports/executive", timeout=90).json()
        assert d["headline"]["revenue_recovered_amount"] == 46000.0, d["headline"]
        assert d["headline"]["revenue_recovered_display"].startswith(RUPEE), d["headline"]

    def test_trend_current_month_bucket_has_recovery(self, client):
        """SCENARIO B: 8 buckets, last (current month) recovered >= 46 (Kunits)."""
        d = client.get(f"{BASE_URL}/api/reports/executive", timeout=90).json()
        trend = d["trend"]
        assert len(trend) == 8, trend
        assert trend[-1]["recovered"] >= 46.0, trend
        assert all(t["recovered"] == 0.0 for t in trend[:-1]), trend

    def test_no_usd_symbol_anywhere(self, client):
        blob = json.dumps(client.get(f"{BASE_URL}/api/overview", timeout=60).json())
        assert "$" not in blob, "USD symbol leaked into INR workspace"


# ---------------------------------------------------------------------------
# SCENARIO D — zero state remains honest on a fresh workspace
# ---------------------------------------------------------------------------
class TestScenarioDZeroState:
    @pytest.fixture(scope="class")
    def client(self):
        return _new_inr_workspace("it6_zero")

    def test_overview_zero_recovered_with_hint(self, client):
        d = client.get(f"{BASE_URL}/api/overview", timeout=60).json()
        rec = _kpi(d["kpis"], "recovered")
        assert rec["value_display"] == f"{RUPEE}0", rec
        assert (rec.get("hint") or "") == "no prior recovery in this dataset", rec
        assert rec.get("amount_type") == "measured", rec

    def test_executive_zero_and_trend_all_zero(self, client):
        d = client.get(f"{BASE_URL}/api/reports/executive", timeout=90).json()
        assert d["headline"]["revenue_recovered_amount"] == 0, d["headline"]
        trend = d["trend"]
        assert len(trend) == 8, trend
        assert all(t["recovered"] == 0.0 for t in trend), trend
        assert d["headline"]["open_pipeline_amount"] > 0, d["headline"]


# ---------------------------------------------------------------------------
# SCENARIO E + F — revenue_recovery contributes; both categories sum
# ---------------------------------------------------------------------------
class TestScenarioEFCategorySums:
    @pytest.fixture(scope="class")
    def client(self):
        return _new_inr_workspace("it6_sum")

    def test_e_revenue_recovery_signal_drives_kpi(self, client):
        sigs = _signals(client)
        rr = [s for s in sigs if s.get("category") == "revenue_recovery"]
        assert rr, [(s["title"], s["category"]) for s in sigs]
        target = rr[0]
        expected = float(target["impact_amount"])
        client.rr_amount = expected
        client.rr_id = target["signal_id"]
        _resolve(client, target["signal_id"])
        d = client.get(f"{BASE_URL}/api/reports/executive", timeout=90).json()
        assert d["headline"]["revenue_recovered_amount"] == expected, (
            d["headline"], target["title"], expected)
        ov = client.get(f"{BASE_URL}/api/overview", timeout=60).json()
        rec = _kpi(ov["kpis"], "recovered")
        assert rec["value_display"].startswith(RUPEE) and rec["value_display"] != f"{RUPEE}0", rec
        assert "1 resolved case" in (rec.get("hint") or ""), rec

    def test_f_both_categories_summed(self, client):
        sigs = _signals(client)
        dup = [s for s in sigs
               if s.get("category") == "profit_leak" and float(s["impact_amount"]) == 46000.0]
        assert dup, [(s["title"], s["category"], s["impact_amount"]) for s in sigs]
        _resolve(client, dup[0]["signal_id"])
        expected = client.rr_amount + 46000.0
        d = client.get(f"{BASE_URL}/api/reports/executive", timeout=90).json()
        assert d["headline"]["revenue_recovered_amount"] == expected, (d["headline"], expected)
        ov = client.get(f"{BASE_URL}/api/overview", timeout=60).json()
        rec = _kpi(ov["kpis"], "recovered")
        assert "2 resolved cases" in (rec.get("hint") or ""), rec
        trend = d["trend"]
        assert trend[-1]["recovered"] >= round(expected / 1000, 1) - 0.1, trend


# ---------------------------------------------------------------------------
# SCENARIO C — deterministic scrub of internal terms, 5 asks
# ---------------------------------------------------------------------------
class TestScenarioCScrub:
    @pytest.fixture(scope="class")
    def client(self):
        return _new_inr_workspace("it6_ai")

    def test_five_asks_no_internal_terms_and_rupee_only(self, client):
        q = "Summarize the biggest recoverable finding and cite records."
        offenders, currency_issues = [], []
        for i in range(5):
            r = client.post(f"{BASE_URL}/api/ai/ask", json={"question": q}, timeout=240)
            assert r.status_code == 200, r.text[:300]
            a = r.json()["answer"]
            found = _leaks(a)
            if found:
                offenders.append((i, found, a[:200]))
            if RUPEE not in a or "$" in a:
                currency_issues.append((i, a[:200]))
        assert not offenders, f"internal-term leaks: {offenders}"
        assert not currency_issues, f"currency issues: {currency_issues}"


# ---------------------------------------------------------------------------
# REGRESSION — USD demo workspace + core endpoints
# ---------------------------------------------------------------------------
class TestUSDDemoRegression:
    def test_demo_overview_usd_zero_recovered(self, demo_client):
        d = demo_client.get(f"{BASE_URL}/api/overview", timeout=60).json()
        assert d["workspace"]["currency"] == "USD"
        assert RUPEE not in json.dumps(d), "rupee leaked into USD workspace"
        rec = _kpi(d["kpis"], "recovered")
        assert rec["value_display"] == "$0", rec

    def test_core_endpoints_200(self, demo_client):
        for path in ("/api/auth/me", "/api/workspace/me", "/api/signals/members",
                     "/api/signals?limit=5"):
            r = demo_client.get(f"{BASE_URL}{path}", timeout=60)
            assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"

    def test_signal_fields_and_assign_status_revert(self, demo_client):
        sigs = demo_client.get(f"{BASE_URL}/api/signals?status=open&limit=5",
                               timeout=60).json()["signals"]
        assert sigs, "no open signals in demo workspace"
        s0 = sigs[0]
        for f in ("owner_email", "due_date", "sla_status"):
            assert f in s0, list(s0.keys())
        sid = s0["signal_id"]
        me = demo_client.get(f"{BASE_URL}/api/auth/me", timeout=30).json()
        email = me.get("email") or me.get("user", {}).get("email")
        r = demo_client.post(f"{BASE_URL}/api/signals/{sid}/assign",
                             json={"owner_email": email}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        r = demo_client.post(f"{BASE_URL}/api/signals/{sid}/status",
                             json={"status": "open"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        r = demo_client.post(f"{BASE_URL}/api/signals/{sid}/assign",
                             json={"owner_email": None}, timeout=60)
        assert r.status_code == 200, r.text[:300]

    def test_duplicate_impact_math_single_excess(self, demo_client):
        sigs = demo_client.get(f"{BASE_URL}/api/signals?limit=50", timeout=60).json()["signals"]
        dups = [s for s in sigs if s.get("detector") == "duplicate_vendor_payment"]
        if not dups:
            pytest.skip("no duplicate signals in demo workspace")
        for s in dups:
            assert float(s["impact_amount"]) > 0, s
            assert s["impact_display"].startswith("$"), s["impact_display"]
