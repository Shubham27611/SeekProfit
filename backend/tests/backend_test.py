"""SeekProfit Stage-2 backend API tests.

Modules covered: auth, workspace/onboarding, overview, signals, ai (Claude), imports.
"""
import io
import re
import uuid

import pytest
import requests

from conftest import BASE_URL, DEMO_EMAIL, DEMO_PASSWORD, auth_session

CATEGORIES = {"revenue_recovery", "profit_leak", "opportunity"}
AMOUNT_TYPES = {"measured", "estimated", "potential"}
URGENCIES = {"low", "medium", "high"}


# --------------------------------------------------------------------------
# Module: health
# --------------------------------------------------------------------------
class TestHealth:
    def test_health(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/health", timeout=30)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# --------------------------------------------------------------------------
# Module: auth (register / login / me / invite)
# --------------------------------------------------------------------------
class TestAuth:
    def test_register_returns_token_and_user(self, fresh_user):
        assert isinstance(fresh_user["token"], str) and len(fresh_user["token"]) > 20
        u = fresh_user["user"]
        assert u["email"] == fresh_user["email"]
        assert "password_hash" not in u
        assert u["workspace"] is not None
        # New workspace must be un-onboarded
        assert u["workspace"]["industry"] is None
        assert u["workspace"]["is_seeded"] is False

    def test_duplicate_register_409(self, api_client, fresh_user):
        r = api_client.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": fresh_user["email"], "password": "Testpass123"},
            timeout=30,
        )
        assert r.status_code == 409, r.text[:300]

    def test_register_short_password_422(self, api_client):
        r = api_client.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": f"test_{uuid.uuid4().hex[:8]}@seekprofit-qa.com", "password": "123"},
            timeout=30,
        )
        assert r.status_code == 422

    def test_login_wrong_password_401(self, api_client, fresh_user):
        r = api_client.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": fresh_user["email"], "password": "definitely-wrong"},
            timeout=30,
        )
        assert r.status_code == 401

    def test_login_unknown_email_401(self, api_client):
        r = api_client.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "nobody_here@seekprofit-qa.com", "password": "whatever1"},
            timeout=30,
        )
        assert r.status_code == 401

    def test_login_success(self, api_client, fresh_user):
        r = api_client.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": fresh_user["email"], "password": fresh_user["password"]},
            timeout=30,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["user"]["email"] == fresh_user["email"]
        assert data["token"]

    def test_me_with_token(self, fresh_user):
        s = auth_session(fresh_user["token"])
        r = s.get(f"{BASE_URL}/api/auth/me", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == fresh_user["email"]
        assert "password_hash" not in data
        assert data["workspace"]["workspace_id"]

    def test_me_without_token_401(self, api_client):
        r = requests.get(f"{BASE_URL}/api/auth/me", timeout=30)
        assert r.status_code == 401

    def test_me_bad_token_401(self):
        s = auth_session("not.a.jwt")
        r = s.get(f"{BASE_URL}/api/auth/me", timeout=30)
        assert r.status_code == 401

    def test_invite_adds_pending_email(self, fresh_user):
        s = auth_session(fresh_user["token"])
        invitee = f"invitee_{uuid.uuid4().hex[:6]}@seekprofit-qa.com"
        r = s.post(f"{BASE_URL}/api/auth/invite", json={"email": invitee}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["invited_email"] == invitee
        # Verify persistence via workspace/me
        ws = s.get(f"{BASE_URL}/api/workspace/me", timeout=30).json()["workspace"]
        assert invitee in ws.get("invited_emails", [])

    def test_bcrypt_hash_format(self):
        """Password hashes must be bcrypt $2b$ (checked in-process)."""
        import sys
        sys.path.insert(0, "/app/backend")
        from core.security import hash_password, verify_password
        h = hash_password("Testpass123")
        assert h.startswith("$2b$"), h[:10]
        assert verify_password("Testpass123", h)
        assert not verify_password("nope", h)


# --------------------------------------------------------------------------
# Module: workspace / onboarding + seeding
# --------------------------------------------------------------------------
class TestWorkspaceSetup:
    def test_workspace_me_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/workspace/me", timeout=30)
        assert r.status_code == 401

    def test_setup_seeds_demo_dataset(self, fresh_user):
        s = auth_session(fresh_user["token"])
        pre = s.get(f"{BASE_URL}/api/workspace/me", timeout=30)
        assert pre.status_code == 200
        assert pre.json()["workspace"]["industry"] is None

        r = s.post(
            f"{BASE_URL}/api/workspace/setup",
            json={
                "business_name": "TEST Seed Co",
                "industry": "ecommerce",
                "currency": "USD",
                "load_demo_data": True,
            },
            timeout=90,
        )
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert body["seeded_records"] >= 150, body["seeded_records"]
        assert body["workspace"]["industry"] == "ecommerce"
        assert body["workspace"]["name"] == "TEST Seed Co"
        assert body["workspace"]["is_seeded"] is True
        assert "_id" not in body["workspace"]

        me = s.get(f"{BASE_URL}/api/workspace/me", timeout=30).json()
        counts = me["counts"]
        assert counts["records"] >= 150, counts
        assert counts["demo_records"] == counts["records"]
        assert counts["csv_records"] == 0
        assert counts["signals"] >= 5, counts

    def test_setup_validation_missing_industry_422(self, fresh_user):
        s = auth_session(fresh_user["token"])
        r = s.post(
            f"{BASE_URL}/api/workspace/setup",
            json={"business_name": "X", "currency": "USD"},
            timeout=30,
        )
        assert r.status_code == 422

    def test_reseed_is_idempotent(self, fresh_user):
        s = auth_session(fresh_user["token"])
        s.post(
            f"{BASE_URL}/api/workspace/setup",
            json={"business_name": "TEST Reseed", "industry": "saas", "load_demo_data": True},
            timeout=90,
        )
        before = s.get(f"{BASE_URL}/api/workspace/me", timeout=30).json()["counts"]
        r = s.post(f"{BASE_URL}/api/workspace/reseed", json={}, timeout=90)
        assert r.status_code == 200, r.text[:300]
        after = s.get(f"{BASE_URL}/api/workspace/me", timeout=30).json()["counts"]
        assert after["records"] == before["records"], (before, after)
        assert after["signals"] == before["signals"]


# --------------------------------------------------------------------------
# Module: overview
# --------------------------------------------------------------------------
class TestOverview:
    def test_overview_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/overview", timeout=30)
        assert r.status_code == 401

    def test_overview_structure(self, seeded_client):
        r = seeded_client.get(f"{BASE_URL}/api/overview", timeout=60)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        for key in ("workspace", "kpis", "trend", "feed", "counts"):
            assert key in d, key

        # KPIs — 4 cards, display strings only
        kpis = d["kpis"]
        assert len(kpis) == 4
        assert {k["slug"] for k in kpis} == {"recovered", "potential", "leaks", "actions"}
        for k in kpis:
            assert isinstance(k["value_display"], str) and k["value_display"], k
            assert isinstance(k["label"], str) and k["label"]
            assert isinstance(k["hint"], str)
        money = {k["slug"]: k["value_display"] for k in kpis}
        assert money["recovered"].startswith("$") or money["recovered"][0].isdigit(), money
        assert money["leaks"].isdigit(), money["leaks"]
        assert money["actions"].isdigit(), money["actions"]

        # Trend — 8 monthly buckets
        trend = d["trend"]
        assert isinstance(trend, list) and len(trend) == 8, len(trend)
        for pt in trend:
            assert "m" in pt and "recovered" in pt and "potential" in pt
            assert isinstance(pt["recovered"], (int, float))
            assert isinstance(pt["potential"], (int, float))

        # Feed
        assert isinstance(d["feed"], list) and len(d["feed"]) > 0
        for f in d["feed"]:
            assert f["id"] and f["title"]
            assert isinstance(f["amount_display"], str)
            assert f["badge"]
        assert d["counts"]["records"] >= 150
        assert d["counts"]["signals_open"] >= 1


# --------------------------------------------------------------------------
# Module: signals (list / filter / detail / status)
# --------------------------------------------------------------------------
class TestSignals:
    def test_signals_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/signals", timeout=30)
        assert r.status_code == 401

    def test_list_sorted_and_shaped(self, seeded_client):
        r = seeded_client.get(f"{BASE_URL}/api/signals", timeout=60)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        sigs = d["signals"]
        assert len(sigs) >= 5, len(sigs)
        scores = [s["priority_score"] for s in sigs]
        assert scores == sorted(scores, reverse=True), scores

        for s in sigs:
            assert s["signal_id"]
            assert s["category"] in CATEGORIES, s["category"]
            assert isinstance(s["impact_display"], str) and s["impact_display"]
            assert s["amount_type"] in AMOUNT_TYPES, s["amount_type"]
            assert 0 <= s["confidence"] <= 1, s["confidence"]
            assert s["urgency"] in URGENCIES, s["urgency"]
            assert 0 <= s["priority_score"] <= 1, s["priority_score"]
            assert isinstance(s["evidence"], list)
            assert "_id" not in s
        # at least one signal carries evidence records with the required fields
        with_ev = [s for s in sigs if s["evidence"]]
        assert with_ev, "no signal has evidence records"
        for ev in with_ev[0]["evidence"]:
            assert ev["record_id"] and ev["type"]
            assert isinstance(ev["amount_display"], str)
            assert "counterparty" in ev

    def test_category_filter(self, seeded_client):
        for cat in CATEGORIES:
            r = seeded_client.get(f"{BASE_URL}/api/signals?category={cat}", timeout=60)
            assert r.status_code == 200
            sigs = r.json()["signals"]
            assert all(s["category"] == cat for s in sigs), cat
        # sanity: leaks present in demo data
        leaks = seeded_client.get(
            f"{BASE_URL}/api/signals?category=profit_leak", timeout=60
        ).json()["signals"]
        assert len(leaks) >= 1

    def test_get_signal_detail_and_404(self, seeded_client):
        sid = seeded_client.get(f"{BASE_URL}/api/signals", timeout=60).json()["signals"][0]["signal_id"]
        r = seeded_client.get(f"{BASE_URL}/api/signals/{sid}", timeout=30)
        assert r.status_code == 200
        assert r.json()["signal_id"] == sid
        r404 = seeded_client.get(f"{BASE_URL}/api/signals/sig_doesnotexist", timeout=30)
        assert r404.status_code == 404

    def test_resolve_removes_from_open_list(self, seeded_client):
        open_sigs = seeded_client.get(
            f"{BASE_URL}/api/signals?status=open", timeout=60
        ).json()["signals"]
        assert open_sigs
        sid = open_sigs[0]["signal_id"]

        r = seeded_client.post(
            f"{BASE_URL}/api/signals/{sid}/status", json={"status": "resolved"}, timeout=30
        )
        assert r.status_code == 200, r.text[:300]

        detail = seeded_client.get(f"{BASE_URL}/api/signals/{sid}", timeout=30).json()
        assert detail["status"] == "resolved"
        assert detail["resolved_at"]

        still_open = seeded_client.get(
            f"{BASE_URL}/api/signals?status=open", timeout=60
        ).json()["signals"]
        assert sid not in [s["signal_id"] for s in still_open]

        resolved = seeded_client.get(
            f"{BASE_URL}/api/signals?status=resolved", timeout=60
        ).json()["signals"]
        assert sid in [s["signal_id"] for s in resolved]

    def test_dismiss_status(self, seeded_client):
        open_sigs = seeded_client.get(
            f"{BASE_URL}/api/signals?status=open", timeout=60
        ).json()["signals"]
        assert open_sigs
        sid = open_sigs[-1]["signal_id"]
        r = seeded_client.post(
            f"{BASE_URL}/api/signals/{sid}/status", json={"status": "dismissed"}, timeout=30
        )
        assert r.status_code == 200
        assert seeded_client.get(f"{BASE_URL}/api/signals/{sid}", timeout=30).json()["status"] == "dismissed"

    def test_invalid_status_400(self, seeded_client):
        sid = seeded_client.get(f"{BASE_URL}/api/signals", timeout=60).json()["signals"][0]["signal_id"]
        r = seeded_client.post(
            f"{BASE_URL}/api/signals/{sid}/status", json={"status": "banana"}, timeout=30
        )
        assert r.status_code == 400, r.status_code

    def test_status_on_unknown_signal_404(self, seeded_client):
        r = seeded_client.post(
            f"{BASE_URL}/api/signals/sig_nope/status", json={"status": "resolved"}, timeout=30
        )
        assert r.status_code == 404


# --------------------------------------------------------------------------
# Module: AI — grounded ask + Claude enrichment
# --------------------------------------------------------------------------
class TestAI:
    def test_ask_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/ai/ask", json={"question": "hi there"}, timeout=30)
        assert r.status_code == 401

    def test_ask_validation_short_question(self, seeded_client):
        r = seeded_client.post(f"{BASE_URL}/api/ai/ask", json={"question": "a"}, timeout=30)
        assert r.status_code == 422

    def test_ask_is_grounded_in_real_records(self, seeded_client):
        r = seeded_client.post(
            f"{BASE_URL}/api/ai/ask",
            json={"question": "What is my single biggest profit leak and which records prove it?"},
            timeout=180,
        )
        assert r.status_code == 200, r.text[:500]
        d = r.json()
        assert isinstance(d["answer"], str) and len(d["answer"]) > 40, d["answer"][:200]
        assert "couldn't reach the analysis service" not in d["answer"], "LLM call failed"
        assert isinstance(d["citations"], list)

        tokens = re.findall(r"\[rec:([a-zA-Z0-9_\-]+)\]", d["answer"])
        assert tokens, f"answer contains no [rec:] token: {d['answer'][:400]}"

        cited_ids = {c["record_id"] for c in d["citations"]}
        assert cited_ids, f"no citations resolved for tokens {tokens}"
        # every returned citation must be a record that really exists in this workspace
        assert cited_ids.issubset(set(tokens))
        for c in d["citations"]:
            assert c["type"] and c["counterparty"]
            assert isinstance(c["amount"], (int, float))
        # at least one emitted token resolved to a real record (no invented IDs dominating)
        assert len(cited_ids) >= 1

    def test_enrich_then_idempotent(self, seeded_client):
        r1 = seeded_client.post(f"{BASE_URL}/api/signals/enrich", json={}, timeout=300)
        assert r1.status_code == 200, r1.text[:400]
        first = r1.json()["enriched"]
        assert first >= 1, first

        sigs = seeded_client.get(f"{BASE_URL}/api/signals", timeout=60).json()["signals"]
        enriched = [s for s in sigs if s["ai_enriched"]]
        assert enriched, "no signal flagged ai_enriched after enrichment"
        assert enriched[0]["explanation"]
        assert enriched[0]["recommended_action"]

        r2 = seeded_client.post(f"{BASE_URL}/api/signals/enrich", json={}, timeout=300)
        assert r2.status_code == 200
        assert r2.json()["enriched"] == 0, r2.json()


# --------------------------------------------------------------------------
# Module: imports (CSV replace workflow)
# --------------------------------------------------------------------------
GOOD_CSV = """type,date,amount,counterparty,memo,status
invoice,2026-01-15,4200,TEST Customer A,Jan invoice,paid
invoice,2026-02-15,5100,TEST Customer B,Feb invoice,unpaid
vendor_bill,2026-01-20,1800,TEST Vendor X,Dup bill,paid
vendor_bill,2026-01-20,1800,TEST Vendor X,Dup bill,paid
vendor_bill,2026-02-05,900,TEST Vendor Y,Software,paid
payment,2026-02-20,4200,TEST Customer A,Payment received,cleared
contract,2026-01-01,12000,TEST Customer C,Annual contract,active
refund,2026-03-02,300,TEST Customer B,Partial refund,processed
"""

BAD_CSV = """foo,bar,baz
1,2,3
4,5,6
"""


class TestImports:
    def test_csv_requires_auth(self):
        r = requests.post(
            f"{BASE_URL}/api/imports/csv",
            files={"file": ("a.csv", GOOD_CSV, "text/csv")},
            timeout=30,
        )
        assert r.status_code == 401

    def test_invalid_csv_400(self, fresh_user):
        s = auth_session(fresh_user["token"])
        s.headers.pop("Content-Type", None)
        r = s.post(
            f"{BASE_URL}/api/imports/csv",
            files={"file": ("bad.csv", BAD_CSV, "text/csv")},
            timeout=60,
        )
        assert r.status_code == 400, f"{r.status_code}: {r.text[:300]}"

    def test_non_csv_extension_400(self, fresh_user):
        s = auth_session(fresh_user["token"])
        s.headers.pop("Content-Type", None)
        r = s.post(
            f"{BASE_URL}/api/imports/csv",
            files={"file": ("data.pdf", b"nope", "application/pdf")},
            timeout=60,
        )
        assert r.status_code == 400

    def test_csv_replaces_dataset(self, seeded_client):
        before = seeded_client.get(f"{BASE_URL}/api/workspace/me", timeout=30).json()["counts"]
        assert before["demo_records"] > 0

        s = requests.Session()
        s.headers.update({"Authorization": seeded_client.headers["Authorization"]})
        r = s.post(
            f"{BASE_URL}/api/imports/csv",
            files={"file": ("test.csv", GOOD_CSV, "text/csv")},
            timeout=120,
        )
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert body["imported_records"] == 8, body
        assert body["generated_signals"] >= 1, body

        after = seeded_client.get(f"{BASE_URL}/api/workspace/me", timeout=30).json()["counts"]
        assert after["csv_records"] == 8, after
        assert after["demo_records"] == 0, after
        assert after["records"] == 8
        assert after["signals"] == body["generated_signals"]

        ws = seeded_client.get(f"{BASE_URL}/api/workspace/me", timeout=30).json()["workspace"]
        assert ws["data_source"] == "csv"

        # duplicate vendor bill detector must fire
        sigs = seeded_client.get(f"{BASE_URL}/api/signals", timeout=60).json()["signals"]
        detectors = {x["detector"] for x in sigs}
        assert "duplicate_vendor_payment" in detectors, detectors

        # overview must still be computable on CSV data
        ov = seeded_client.get(f"{BASE_URL}/api/overview", timeout=60)
        assert ov.status_code == 200
        assert ov.json()["counts"]["records"] == 8


# --------------------------------------------------------------------------
# Module: pre-existing demo account (used by frontend tests)
# --------------------------------------------------------------------------
class TestDemoAccount:
    def test_demo_login_and_data(self, demo_client):
        me = demo_client.get(f"{BASE_URL}/api/auth/me", timeout=30)
        assert me.status_code == 200
        assert me.json()["email"] == DEMO_EMAIL
        ws = demo_client.get(f"{BASE_URL}/api/workspace/me", timeout=30).json()
        assert ws["workspace"]["industry"] is not None, "demo account not onboarded"
        assert ws["counts"]["records"] >= 150, ws["counts"]
        assert ws["counts"]["signals"] >= 5, ws["counts"]
