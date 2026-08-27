"""Iteration 5: Revenue Recovered KPI must be ONLY the sum of resolved
revenue_recovery signal impacts (no 12% baseline), plus AI groundedness
(no leaking of internal brief/field names)."""
import json
import re
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

LEAK_WORDS = ["the brief", "dataset_facts", "prior_recovery_available", "the json"]


def _new_inr_workspace(api_client, prefix="grnd"):
    email = f"{prefix}_{uuid.uuid4().hex[:8]}@seekprofit.app"
    r = api_client.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "testpass123", "name": "TEST Grounding QA"},
        timeout=30,
    )
    assert r.status_code == 200, f"register failed {r.status_code}: {r.text[:300]}"
    token = r.json()["token"]
    s = auth_session(token)
    s.jwt = token
    s.email = email
    r = s.post(
        f"{BASE_URL}/api/workspace/setup",
        json={"business_name": "TEST Grounding Co", "industry": "saas",
              "currency": "USD", "load_demo_data": False},
        timeout=90,
    )
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


def _leaks(text):
    low = text.lower()
    return [w for w in LEAK_WORDS if w in low]


# ---------------------------------------------------------------------------
# module: services/finance.py compute_kpis / build_trend — measured-only KPI
# ---------------------------------------------------------------------------
class TestUnresolvedWorkspaceShowsZeroRecovered:
    @pytest.fixture(scope="class")
    def client(self, api_client):
        return _new_inr_workspace(api_client, "grnd_zero")

    def test_overview_recovered_is_zero_with_hint(self, client):
        r = client.get(f"{BASE_URL}/api/overview", timeout=60)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d["workspace"]["currency"] == "INR", d["workspace"]
        kpis = d["kpis"]
        rec = _kpi(kpis, "recovered")
        assert rec["value_display"] == f"{RUPEE}0", rec
        assert "no prior recovery" in (rec.get("hint") or "").lower(), rec
        pot = _kpi(kpis, "potential")
        assert pot["value_display"].startswith(RUPEE), pot
        amt = float(re.sub(r"[^\d.]", "", pot["value_display"]))
        assert amt > 0, pot
        leaks = _kpi(kpis, "leaks")
        actions = _kpi(kpis, "actions")
        assert leaks["value_display"] is not None and actions["value_display"] is not None
        assert int(leaks["value_display"]) >= 0
        assert int(actions["value_display"]) >= 0

    def test_executive_report_zero_recovered_positive_pipeline(self, client):
        r = client.get(f"{BASE_URL}/api/reports/executive", timeout=90)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        h = d["headline"]
        assert h["revenue_recovered_amount"] == 0, h
        assert h["revenue_recovered_display"] == f"{RUPEE}0", h
        assert h["open_pipeline_amount"] > 0, h
        trend = d["trend"]
        assert trend, "empty trend"
        assert all(t["recovered"] == 0.0 for t in trend), trend
        assert any(t["potential"] > 0 for t in trend[-3:]), trend

    def test_signals_potential_duplicates_in_rupees(self, client):
        r = client.get(f"{BASE_URL}/api/signals?limit=50", timeout=60)
        assert r.status_code == 200, r.text[:400]
        sigs = r.json()["signals"]
        dups = [s for s in sigs if s.get("detector") == "duplicate_vendor_payment"]
        assert dups, [s["title"] for s in sigs]
        impacts = sorted(float(s["impact_amount"]) for s in dups)
        assert impacts == [27500.0, 46000.0], impacts
        for s in dups:
            assert s["title"].startswith("Potential duplicate payment"), s["title"]
        blob = json.dumps(r.json())
        assert "$" not in blob, "USD symbol leaked into /api/signals"
        for s in sigs:
            assert s["impact_display"].startswith(RUPEE), s["impact_display"]

    def test_ai_prior_recovery_before_resolve_states_none(self, client):
        r = client.post(f"{BASE_URL}/api/ai/ask",
                        json={"question": "How much has this business previously recovered?"},
                        timeout=180)
        assert r.status_code == 200, r.text[:400]
        answer = r.json()["answer"]
        low = answer.lower()
        keys = ["no prior recovery", "no recovery", "not available", "does not contain",
                "no record", "nothing has been recovered", "no amount", "zero"]
        assert any(k in low for k in keys), f"did not disclaim prior recovery: {answer}"
        assert not _leaks(answer), f"internal names leaked {_leaks(answer)}: {answer}"

    def test_ai_largest_finding_currency_and_grounding(self, client):
        q = "What is the largest high-confidence finding and how much can we recover?"
        r = client.post(f"{BASE_URL}/api/ai/ask", json={"question": q}, timeout=180)
        assert r.status_code == 200, r.text[:400]
        answer = r.json()["answer"]
        if "$" in answer or RUPEE not in answer:
            r = client.post(f"{BASE_URL}/api/ai/ask", json={"question": q}, timeout=180)
            assert r.status_code == 200, r.text[:400]
            answer = r.json()["answer"]
        assert RUPEE in answer, answer
        assert "$" not in answer, answer
        assert not _leaks(answer), f"internal names leaked {_leaks(answer)}: {answer}"
        low = answer.lower()
        grounding = ["based on", "transactions", "high-confidence", "high confidence",
                     "potential", "requires review", "the current dataset", "dataset",
                     "imported records"]
        assert any(g in low for g in grounding), answer


# ---------------------------------------------------------------------------
# resolve a signal -> KPI must reflect exactly that impact
# ---------------------------------------------------------------------------
class TestResolvedSignalDrivesRecoveredKPI:
    @pytest.fixture(scope="class")
    def resolved(self, api_client):
        """Resolve the Cloud Vendor duplicate (46000, category=profit_leak)."""
        c = _new_inr_workspace(api_client, "grnd_res")
        sigs = c.get(f"{BASE_URL}/api/signals?limit=50", timeout=60).json()["signals"]
        target = [s for s in sigs
                  if s.get("detector") == "duplicate_vendor_payment"
                  and float(s["impact_amount"]) == 46000.0]
        assert target, [(s["title"], s["impact_amount"]) for s in sigs]
        sid = target[0]["signal_id"]
        r = c.post(f"{BASE_URL}/api/signals/{sid}/status",
                   json={"status": "resolved"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        c.resolved_id = sid
        c.all_signals = sigs
        return c

    def test_overview_recovered_equals_resolved_impact(self, resolved):
        """SPEC: resolving the ₹46,000 duplicate must headline ₹46,000 recovered."""
        d = resolved.get(f"{BASE_URL}/api/overview", timeout=60).json()
        rec = _kpi(d["kpis"], "recovered")
        assert rec["value_display"] in (f"{RUPEE}46,000", f"{RUPEE}46.0K"), (
            "compute_kpis() only sums category=='revenue_recovery'; the duplicate-payment "
            f"signal is category=='profit_leak' so recovering cash never moves the KPI -> {rec}")
        assert "no prior recovery" not in (rec.get("hint") or "").lower(), rec

    def test_executive_recovered_amount_is_46000(self, resolved):
        d = resolved.get(f"{BASE_URL}/api/reports/executive", timeout=90).json()
        assert d["headline"]["revenue_recovered_amount"] == 46000.0, d["headline"]

    def test_trend_recovered_reflects_resolution(self, resolved):
        """build_trend() must show the resolved amount in the current month bucket."""
        d = resolved.get(f"{BASE_URL}/api/reports/executive", timeout=90).json()
        trend = d["trend"]
        assert any(t["recovered"] > 0 for t in trend), (
            "trend buckets exclude the current month (cursor arithmetic uses 31/32-day "
            f"steps), so a just-resolved signal never appears: {trend}")

    def test_revenue_recovery_category_resolution_moves_kpi(self, resolved):
        """Positive control: resolving a revenue_recovery signal DOES move the KPI.
        Iteration 6: recovery-eligible categories are {revenue_recovery, profit_leak},
        so the expected total is the already-resolved 46,000 duplicate PLUS this one."""
        rr = [s for s in resolved.all_signals if s["category"] == "revenue_recovery"]
        assert rr, [s["category"] for s in resolved.all_signals]
        target = rr[0]
        r = resolved.post(f"{BASE_URL}/api/signals/{target['signal_id']}/status",
                          json={"status": "resolved"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        expected = 46000.0 + float(target["impact_amount"])
        d = resolved.get(f"{BASE_URL}/api/reports/executive", timeout=90).json()
        try:
            assert d["headline"]["revenue_recovered_amount"] == expected, (
                d["headline"], expected)
            ov = resolved.get(f"{BASE_URL}/api/overview", timeout=60).json()
            rec = _kpi(ov["kpis"], "recovered")
            assert rec["value_display"].startswith(RUPEE) and rec["value_display"] != f"{RUPEE}0", rec
            assert "2 resolved cases" in (rec.get("hint") or ""), rec
        finally:
            # revert so the AI test below sees a stable single-resolution state
            resolved.post(f"{BASE_URL}/api/signals/{target['signal_id']}/status",
                          json={"status": "open"}, timeout=60)

    def test_ai_acknowledges_resolved_recovery(self, resolved):
        r = resolved.post(f"{BASE_URL}/api/ai/ask",
                          json={"question": "How much has this business previously recovered?"},
                          timeout=180)
        assert r.status_code == 200, r.text[:400]
        answer = r.json()["answer"]
        assert RUPEE in answer, answer
        assert not _leaks(answer), f"internal names leaked {_leaks(answer)}: {answer}"
        assert "46,000" in answer or "46000" in answer or "46.0" in answer, answer

    def test_ai_never_leaks_internal_field_names(self, resolved):
        """Fix (b): answers must never name the brief or its internal fields."""
        offenders = []
        for q in ("How much has this business previously recovered?",
                  "Summarise our recovery history and what is still open.",
                  "What is the largest high-confidence finding?"):
            r = resolved.post(f"{BASE_URL}/api/ai/ask", json={"question": q}, timeout=180)
            assert r.status_code == 200, r.text[:300]
            a = r.json()["answer"]
            found = _leaks(a)
            if found:
                offenders.append((q, found, a[:220]))
        assert not offenders, f"internal-name leaks in {len(offenders)}/3 answers: {offenders}"


# ---------------------------------------------------------------------------
# regression: USD demo workspace — recovered now $0 (intentional change)
# ---------------------------------------------------------------------------
class TestDemoUSDRegression:
    def test_demo_overview_usd_and_zero_recovered(self, demo_client):
        r = demo_client.get(f"{BASE_URL}/api/overview", timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["workspace"]["currency"] == "USD"
        assert RUPEE not in json.dumps(d), "rupee leaked into USD workspace"
        rec = _kpi(d["kpis"], "recovered")
        assert rec["value_display"] == "$0", rec
        for f in d["feed"]:
            assert f["amount_display"].startswith("$"), f

    def test_core_endpoints_still_200(self, demo_client):
        for path in ("/api/auth/me", "/api/workspace/me", "/api/signals/members"):
            r = demo_client.get(f"{BASE_URL}{path}", timeout=60)
            assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"

    def test_assign_status_enrich_and_revert(self, demo_client):
        sigs = demo_client.get(f"{BASE_URL}/api/signals?status=open&limit=5",
                               timeout=60).json()["signals"]
        assert sigs, "no open signals in demo workspace"
        s0 = sigs[0]
        for f in ("owner_email", "due_date", "sla_status"):
            assert f in s0, s0.keys()
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
        r = demo_client.post(f"{BASE_URL}/api/signals/enrich", json={}, timeout=240)
        assert 200 <= r.status_code < 300, f"enrich -> {r.status_code} {r.text[:300]}"

    def test_stream_sse_open_and_done(self, api_client):
        r = api_client.post(f"{BASE_URL}/api/auth/login",
                            json={"email": "cfo@demo.seekprofit.app", "password": "demo1234"},
                            timeout=30)
        assert r.status_code == 200, r.text[:300]
        token = r.json()["token"]
        events, done = [], None
        with requests.get(f"{BASE_URL}/api/ai/ask/stream",
                          params={"token": token, "question": "What is the biggest profit leak?"},
                          stream=True, timeout=180) as resp:
            assert resp.status_code == 200, resp.text[:300]
            assert "text/event-stream" in resp.headers.get("content-type", "")
            event = None
            for raw in resp.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                line = raw.strip()
                if line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                    events.append(event)
                elif line.startswith("data:") and event == "done":
                    done = json.loads(line.split(":", 1)[1].strip())
                    break
                elif line.startswith("data:") and event == "error":
                    pytest.fail(f"stream error: {line[:300]}")
        assert "open" in events, events
        assert done is not None and done.get("text", "").strip(), done
        assert not _leaks(done["text"]), _leaks(done["text"])
