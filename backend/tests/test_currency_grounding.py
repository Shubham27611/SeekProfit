"""Currency propagation (CSV -> workspace -> KPIs/signals/reports/AI) + AI groundedness tests."""
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


def _walk_displays(obj, path="$"):
    """Yield (path, value) for every key ending in _display."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.endswith("_display") and isinstance(v, str):
                yield (f"{path}.{k}", v)
            else:
                yield from _walk_displays(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_displays(v, f"{path}[{i}]")


# ---------------------------------------------------------------------------
# module: routers/imports.py + overview/signals/reports currency propagation
# ---------------------------------------------------------------------------
class TestINRCurrencyFlow:
    @pytest.fixture(scope="class")
    def inr_client(self, api_client):
        email = f"curr_qa_{uuid.uuid4().hex[:8]}@seekprofit.app"
        r = api_client.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": email, "password": "testpass123", "name": "TEST Currency QA"},
            timeout=30,
        )
        assert r.status_code == 200, f"register failed {r.status_code}: {r.text[:300]}"
        s = auth_session(r.json()["token"])
        # onboarding with USD on purpose -> CSV must flip it to INR
        r = s.post(
            f"{BASE_URL}/api/workspace/setup",
            json={
                "business_name": "TEST Currency Co",
                "industry": "saas",
                "currency": "USD",
                "load_demo_data": False,
            },
            timeout=90,
        )
        assert r.status_code == 200, f"setup failed {r.status_code}: {r.text[:300]}"
        s.email = email
        return s

    @pytest.fixture(scope="class")
    def imported(self, inr_client):
        files = {"file": ("inr.csv", INR_CSV.encode(), "text/csv")}
        sess = requests.Session()
        sess.headers.update({"Authorization": inr_client.headers["Authorization"]})
        r = sess.post(f"{BASE_URL}/api/imports/csv", files=files, timeout=120)
        assert r.status_code == 200, f"csv import failed {r.status_code}: {r.text[:400]}"
        return r.json()

    def test_csv_import_returns_inr(self, imported):
        assert imported["ok"] is True
        assert imported["currency"] == "INR", imported
        assert imported["imported_records"] == 9
        assert imported["generated_signals"] >= 1

    def test_overview_uses_rupee(self, inr_client, imported):
        r = inr_client.get(f"{BASE_URL}/api/overview", timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["workspace"]["currency"] == "INR"
        assert data["workspace"]["data_source"] == "csv"
        assert data["kpis"], "no kpis returned"
        for k in data["kpis"]:
            vd = k["value_display"]
            if k.get("amount_type") == "count":
                continue
            assert RUPEE in vd and "$" not in vd, f"kpi {k.get('key')} -> {vd}"
        for k in data["kpis"]:
            if k.get("supporting_amount"):
                assert "$" not in k["supporting_amount"], k
        assert data["feed"], "empty feed"
        for f in data["feed"]:
            assert f["amount_display"].startswith(RUPEE), f
        bad = [(p, v) for p, v in _walk_displays(data) if "$" in v]
        assert not bad, f"USD symbols leaked in /api/overview: {bad}"

    def test_signals_use_rupee_and_potential_wording(self, inr_client, imported):
        r = inr_client.get(f"{BASE_URL}/api/signals?limit=50", timeout=60)
        assert r.status_code == 200, r.text[:300]
        sigs = r.json()["signals"]
        assert sigs
        for s in sigs:
            assert s["impact_display"].startswith(RUPEE), s["impact_display"]
            for ev in s.get("evidence", []):
                assert ev["amount_display"].startswith(RUPEE), ev
        bad = [(p, v) for p, v in _walk_displays(r.json()) if "$" in v]
        assert not bad, f"USD symbols leaked in /api/signals: {bad}"

        dups = [s for s in sigs if s.get("detector") == "duplicate_vendor_payment"]
        assert dups, f"no duplicate signal found: {[s['title'] for s in sigs]}"
        for d in dups:
            assert d["title"].startswith("Potential duplicate payment"), d["title"]
            assert not d["title"].lower().startswith("duplicate payment to")
            # pair cluster -> impact == single payment amount
            assert float(d["impact_amount"]) in (27500.0, 46000.0), d["impact_amount"]

    def test_executive_report_uses_rupee(self, inr_client, imported):
        r = inr_client.get(f"{BASE_URL}/api/reports/executive", timeout=90)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["workspace"]["currency"] == "INR"
        assert d["headline"]["revenue_recovered_display"].startswith(RUPEE)
        assert d["headline"]["open_pipeline_display"].startswith(RUPEE)
        for c in d["category_totals"]:
            assert c["open_impact_display"].startswith(RUPEE), c
        for a in d["top_actions"]:
            assert a["impact_display"].startswith(RUPEE), a
        for c in d["top_counterparties"]["customers"]:
            assert c["invoiced_display"].startswith(RUPEE), c
        for v in d["top_counterparties"]["vendors"]:
            assert v["spend_display"].startswith(RUPEE), v
        bad = [(p, v) for p, v in _walk_displays(d) if "$" in v]
        assert not bad, f"USD symbols leaked in /api/reports/executive: {bad}"


# ---------------------------------------------------------------------------
# module: routers/ai.py + services/llm_analyst.py — currency + groundedness
# ---------------------------------------------------------------------------
FORBIDDEN = ["confirmed duplicate", "has already recovered", "previously recovered", "has recovered"]
GROUNDING = ["based on", "transactions", "high-confidence", "high confidence",
             "potential", "likely", "requires review", "in the dataset", "dataset"]
# Negations such as "not confirmed duplicates" / "no previously recovered amount" are legitimate.
_NEGATORS = ("not ", "no ", "never ", "aren't ", "isn't ", "rather than ", "instead of ", "without ",
             "zero ", "0 ", RUPEE + "0", "$0")


def ungrounded_phrases(text: str) -> list:
    low = text.lower()
    hits = []
    for phrase in FORBIDDEN:
        for m in re.finditer(re.escape(phrase), low):
            window = low[max(0, m.start() - 30):m.start()]
            if any(neg in window for neg in _NEGATORS):
                continue
            hits.append(phrase)
            break
    return hits


class TestAIGrounding:
    @pytest.fixture(scope="class")
    def inr_client(self, api_client):
        email = f"curr_ai_{uuid.uuid4().hex[:8]}@seekprofit.app"
        r = api_client.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": email, "password": "testpass123", "name": "TEST AI QA"},
            timeout=30,
        )
        assert r.status_code == 200, r.text[:300]
        token = r.json()["token"]
        s = auth_session(token)
        r = s.post(
            f"{BASE_URL}/api/workspace/setup",
            json={"business_name": "TEST AI Co", "industry": "saas",
                  "currency": "USD", "load_demo_data": False},
            timeout=90,
        )
        assert r.status_code == 200, r.text[:300]
        files = {"file": ("inr.csv", INR_CSV.encode(), "text/csv")}
        up = requests.Session()
        up.headers.update({"Authorization": f"Bearer {token}"})
        r = up.post(f"{BASE_URL}/api/imports/csv", files=files, timeout=120)
        assert r.status_code == 200, r.text[:400]
        assert r.json()["currency"] == "INR"
        s.jwt = token
        return s

    def _ask(self, client, question, timeout=180):
        return client.post(f"{BASE_URL}/api/ai/ask", json={"question": question}, timeout=timeout)

    def test_ask_largest_finding_currency_and_grounding(self, inr_client):
        q = "What is the largest high-confidence finding and how much can we recover?"
        r = self._ask(inr_client, q)
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        answer = data["answer"]
        assert answer.strip(), "empty answer"
        if "$" in answer or RUPEE not in answer:
            # retry once per instructions (LLM non-determinism)
            r = self._ask(inr_client, q)
            assert r.status_code == 200, r.text[:400]
            data = r.json()
            answer = data["answer"]
        assert RUPEE in answer, f"no rupee sign in answer: {answer}"
        assert "$" not in answer, f"USD symbol in answer: {answer}"
        low = answer.lower()
        found = ungrounded_phrases(answer)
        assert not found, f"ungrounded phrase(s) {found} in: {answer}"
        assert any(g in low for g in GROUNDING), f"no grounding phrase in: {answer}"
        cites = data.get("citations", [])
        assert cites, f"no citations returned: {answer}"
        assert any(c["amount_display"].startswith(RUPEE) for c in cites), cites
        for c in cites:
            assert "$" not in c["amount_display"], c

    def test_ask_prior_recovery_not_fabricated(self, inr_client):
        r = self._ask(inr_client, "How much has this business previously recovered?")
        assert r.status_code == 200, r.text[:400]
        answer = r.json()["answer"]
        low = answer.lower()
        keys = ["no prior recovery", "no recovery history", "not available", "insufficient data",
                "no recovery", "does not contain", "no data", "not present", "isn't available",
                "is not available", "no record"]
        assert any(k in low for k in keys), f"did not disclaim missing prior recovery: {answer}"
        bad = ungrounded_phrases(answer)
        assert not bad, f"fabricated recovery claim {bad}: {answer}"
        # no fabricated recovered figure: reject "recovered <sym><num>" patterns
        m = re.search(r"(recovered|recovery of)\s*(?:is|was|:)?\s*[" + RUPEE + r"$]\s?[\d,]+", low)
        assert not m, f"fabricated recovery figure: {m.group(0)} in {answer}"

    def test_ask_stream_currency_and_grounding(self, inr_client):
        q = "What is the biggest potential duplicate payment?"
        url = f"{BASE_URL}/api/ai/ask/stream"
        deltas, done = [], None
        with requests.get(url, params={"token": inr_client.jwt, "question": q},
                          stream=True, timeout=180) as resp:
            assert resp.status_code == 200, resp.text[:300]
            assert "text/event-stream" in resp.headers.get("content-type", "")
            event = None
            for raw in resp.iter_lines(decode_unicode=True):
                if raw is None:
                    continue
                line = raw.strip()
                if line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    payload = line.split(":", 1)[1].strip()
                    if event == "delta":
                        deltas.append(json.loads(payload).get("text", ""))
                    elif event == "done":
                        done = json.loads(payload)
                        break
                    elif event == "error":
                        pytest.fail(f"stream error event: {payload[:300]}")
        assert deltas, "no delta events received"
        assert done is not None, "no done event received"
        text = done["text"]
        assert text.strip(), "empty done text"
        assert RUPEE in text, f"no rupee in stream text: {text}"
        assert "$" not in text, f"USD symbol in stream text: {text}"
        bad = ungrounded_phrases(text)
        assert not bad, f"ungrounded phrase(s) {bad}: {text}"
        for c in done.get("citations", []):
            assert c["amount_display"].startswith(RUPEE), c


# ---------------------------------------------------------------------------
# regression: existing USD demo workspace must remain USD
# ---------------------------------------------------------------------------
class TestUSDRegression:
    def test_demo_overview_still_usd(self, demo_client):
        r = demo_client.get(f"{BASE_URL}/api/overview", timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["workspace"]["currency"] == "USD", d["workspace"]
        money_kpis = [k for k in d["kpis"] if k.get("amount_type") != "count"]
        assert money_kpis
        for k in money_kpis:
            assert k["value_display"].startswith("$"), k
        for f in d["feed"]:
            assert f["amount_display"].startswith("$"), f
        assert RUPEE not in json.dumps(d), "rupee leaked into USD workspace"

    def test_demo_signals_and_report_usd(self, demo_client):
        r = demo_client.get(f"{BASE_URL}/api/signals?limit=20", timeout=60)
        assert r.status_code == 200
        sigs = r.json()["signals"]
        assert sigs
        for s in sigs:
            assert s["impact_display"].startswith("$"), s["impact_display"]
            assert "owner_email" in s and "due_date" in s and "sla_status" in s
        r = demo_client.get(f"{BASE_URL}/api/reports/executive", timeout=90)
        assert r.status_code == 200
        assert r.json()["headline"]["revenue_recovered_display"].startswith("$")

    def test_core_endpoints_still_200(self, demo_client):
        for path in ("/api/auth/me", "/api/workspace/me", "/api/signals/members"):
            r = demo_client.get(f"{BASE_URL}{path}", timeout=60)
            assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"

    def test_assign_and_status_endpoints(self, demo_client):
        r = demo_client.get(f"{BASE_URL}/api/signals?status=open&limit=5", timeout=60)
        assert r.status_code == 200
        sigs = r.json()["signals"]
        assert sigs, "no open signals in demo workspace"
        sid = sigs[0]["signal_id"]
        me = demo_client.get(f"{BASE_URL}/api/auth/me", timeout=30).json()
        email = me.get("email") or me.get("user", {}).get("email")
        r = demo_client.post(f"{BASE_URL}/api/signals/{sid}/assign",
                             json={"owner_email": email}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        r = demo_client.post(f"{BASE_URL}/api/signals/{sid}/status",
                             json={"status": "open"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        # cleanup: unassign
        r = demo_client.post(f"{BASE_URL}/api/signals/{sid}/assign",
                             json={"owner_email": None}, timeout=60)
        assert r.status_code == 200, r.text[:300]


# ---------------------------------------------------------------------------
# edge cases: CSV without a currency column, mixed currencies, onboarding currency
# ---------------------------------------------------------------------------
NO_CUR_CSV = """type,date,amount,counterparty,memo,status
vendor_bill,2026-02-01,5000,Vendor A,Service,paid
vendor_bill,2026-02-02,5000,Vendor A,Service,paid
invoice,2026-02-03,9000,Client B,Retainer,paid
"""

MIXED_CSV = """type,date,amount,counterparty,memo,status,currency
vendor_bill,2026-03-01,5000,Vendor A,Service,paid,EUR
vendor_bill,2026-03-02,5000,Vendor A,Service,paid,EUR
invoice,2026-03-03,9000,Client B,Retainer,paid,EUR
invoice,2026-03-04,7000,Client C,Retainer,paid,USD
"""


def _new_workspace(api_client, currency="USD", demo=False):
    email = f"curr_edge_{uuid.uuid4().hex[:8]}@seekprofit.app"
    r = api_client.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "testpass123", "name": "TEST Edge"},
        timeout=30,
    )
    assert r.status_code == 200, r.text[:300]
    token = r.json()["token"]
    s = auth_session(token)
    r = s.post(
        f"{BASE_URL}/api/workspace/setup",
        json={"business_name": "TEST Edge Co", "industry": "saas",
              "currency": currency, "load_demo_data": demo},
        timeout=90,
    )
    assert r.status_code == 200, r.text[:300]
    s.jwt = token
    return s


def _upload(client, body):
    up = requests.Session()
    up.headers.update({"Authorization": client.headers["Authorization"]})
    return up.post(f"{BASE_URL}/api/imports/csv",
                   files={"file": ("t.csv", body.encode(), "text/csv")}, timeout=120)


class TestCurrencyEdgeCases:
    def test_csv_without_currency_column_falls_back_to_usd(self, api_client):
        c = _new_workspace(api_client, currency="INR")
        r = _upload(c, NO_CUR_CSV)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["currency"] == "USD", r.json()
        d = c.get(f"{BASE_URL}/api/overview", timeout=60).json()
        assert d["workspace"]["currency"] == "USD"
        assert all(f["amount_display"].startswith("$") for f in d["feed"]), d["feed"]

    def test_mixed_csv_uses_dominant_currency(self, api_client):
        c = _new_workspace(api_client)
        r = _upload(c, MIXED_CSV)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["currency"] == "EUR", r.json()
        d = c.get(f"{BASE_URL}/api/overview", timeout=60).json()
        assert d["workspace"]["currency"] == "EUR"
        for f in d["feed"]:
            assert f["amount_display"].startswith("\u20ac"), f
        sigs = c.get(f"{BASE_URL}/api/signals?limit=20", timeout=60).json()["signals"]
        assert sigs
        for s in sigs:
            assert s["impact_display"].startswith("\u20ac"), s["impact_display"]

    def test_onboarding_currency_respected_for_demo_data(self, api_client):
        c = _new_workspace(api_client, currency="GBP", demo=True)
        d = c.get(f"{BASE_URL}/api/overview", timeout=60).json()
        assert d["workspace"]["currency"] == "GBP"
        money = [k for k in d["kpis"] if k.get("amount_type") != "count"]
        for k in money:
            assert k["value_display"].startswith("\u00a3"), k
        for f in d["feed"]:
            assert f["amount_display"].startswith("\u00a3"), f


# ---------------------------------------------------------------------------
# module: routers/signals.py POST /enrich — LLM explanations must use the
# workspace currency and grounded wording.
# ---------------------------------------------------------------------------
class TestSignalEnrichCurrency:
    @pytest.fixture(scope="class")
    def inr_client(self, api_client):
        c = _new_workspace(api_client, currency="USD")
        r = _upload(c, INR_CSV)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["currency"] == "INR"
        return c

    def test_fallback_explanations_use_rupee(self, inr_client):
        sigs = inr_client.get(f"{BASE_URL}/api/signals?limit=50", timeout=60).json()["signals"]
        assert sigs
        for s in sigs:
            blob = f"{s['explanation']} {s['recommended_action']}"
            assert "$" not in blob, f"USD symbol in rule explanation: {s['title']} -> {blob}"

    def test_enriched_explanations_use_rupee(self, inr_client):
        r = inr_client.post(f"{BASE_URL}/api/signals/enrich", json={}, timeout=240)
        assert r.status_code == 200, r.text[:400]
        sigs = inr_client.get(f"{BASE_URL}/api/signals?limit=50", timeout=60).json()["signals"]
        enriched = [s for s in sigs if s.get("ai_enriched")]
        assert enriched, f"no signals enriched: {r.json()}"
        offenders = []
        for s in enriched:
            blob = f"{s['explanation']} {s['recommended_action']}"
            if "$" in blob:
                offenders.append((s["title"], blob[:200]))
            bad = ungrounded_phrases(blob)
            assert not bad, f"ungrounded phrase {bad} in {s['title']}: {blob}"
        assert not offenders, f"USD symbol in AI explanations: {offenders}"
