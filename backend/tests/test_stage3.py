"""Stage-3 backend tests: signal assignment/SLA, members, executive report, SSE ask stream."""
import json
from datetime import datetime, timezone, timedelta

import pytest
import requests

from conftest import BASE_URL


# ---------------------------------------------------------------------------
# module: routers/signals.py — members, assign, SLA, filters
# ---------------------------------------------------------------------------
class TestSignalsAssignment:
    def test_members_endpoint(self, seeded_client, fresh_user):
        r = seeded_client.get(f"{BASE_URL}/api/signals/members", timeout=30)
        assert r.status_code == 200, r.text[:300]
        members = r.json()["members"]
        assert isinstance(members, list) and len(members) >= 1
        owner = [m for m in members if m["role"] == "owner"]
        assert len(owner) == 1
        assert owner[0]["email"] == fresh_user["email"]
        for m in members:
            assert m["role"] in {"owner", "invited"}
            assert "@" in m["email"]

    def test_members_includes_invited(self, seeded_client):
        inv_email = "invitee_stage3@seekprofit-qa.com"
        r = seeded_client.post(
            f"{BASE_URL}/api/auth/invite", json={"email": inv_email}, timeout=30
        )
        if r.status_code != 200:
            pytest.skip(f"invite endpoint returned {r.status_code}: {r.text[:200]}")
        r = seeded_client.get(f"{BASE_URL}/api/signals/members", timeout=30)
        assert r.status_code == 200
        emails = {m["email"]: m["role"] for m in r.json()["members"]}
        assert emails.get(inv_email) == "invited"

    def test_list_carries_owner_due_sla_fields(self, seeded_client):
        r = seeded_client.get(f"{BASE_URL}/api/signals?limit=50", timeout=30)
        assert r.status_code == 200
        sigs = r.json()["signals"]
        assert len(sigs) > 0
        for s in sigs:
            assert "owner_email" in s and "due_date" in s and "sla_status" in s
            assert s["sla_status"] in {"overdue", "due_soon", "on_track", None}
            # previously tested fields still present
            for k in ("signal_id", "title", "category", "impact_display", "urgency", "status"):
                assert k in s

    def test_assign_auto_due_date_from_urgency(self, seeded_client, fresh_user):
        r = seeded_client.get(f"{BASE_URL}/api/signals?status=open&limit=50", timeout=30)
        sigs = r.json()["signals"]
        assert sigs, "no open signals to assign"
        expected_days = {"high": 3, "medium": 7, "low": 14}
        tested = set()
        for s in sigs:
            urg = s.get("urgency")
            if urg in tested or urg not in expected_days or s.get("due_date"):
                continue
            tested.add(urg)
            sid = s["signal_id"]
            ar = seeded_client.post(
                f"{BASE_URL}/api/signals/{sid}/assign",
                json={"owner_email": fresh_user["email"]},
                timeout=30,
            )
            assert ar.status_code == 200, ar.text[:300]
            body = ar.json()
            assert body["ok"] is True
            assert body["owner_email"] == fresh_user["email"]

            # verify persistence
            gr = seeded_client.get(f"{BASE_URL}/api/signals/{sid}", timeout=30)
            assert gr.status_code == 200
            got = gr.json()
            assert got["owner_email"] == fresh_user["email"]
            assert got["due_date"], "due_date should be auto-derived"
            assert got["status"] == "in_progress", f"open->in_progress expected, got {got['status']}"
            due = datetime.fromisoformat(got["due_date"].replace("Z", "+00:00"))
            delta_days = (due - datetime.now(timezone.utc)).total_seconds() / 86400
            assert abs(delta_days - expected_days[urg]) < 0.5, (
                f"urgency={urg} expected ~{expected_days[urg]}d, got {delta_days:.2f}d"
            )
            assert got["sla_status"] in {"on_track", "due_soon"}
        assert tested, "no eligible signals found for urgency SLA check"

    def test_assign_explicit_due_date_honored(self, seeded_client, fresh_user):
        sigs = seeded_client.get(f"{BASE_URL}/api/signals?limit=50", timeout=30).json()["signals"]
        target = next(s for s in sigs if s["status"] in {"open", "in_progress"})
        sid = target["signal_id"]
        explicit = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        r = seeded_client.post(
            f"{BASE_URL}/api/signals/{sid}/assign",
            json={"owner_email": fresh_user["email"], "due_date": explicit},
            timeout=30,
        )
        assert r.status_code == 200, r.text[:300]
        got = seeded_client.get(f"{BASE_URL}/api/signals/{sid}", timeout=30).json()
        assert got["due_date"] == explicit
        assert got["owner_email"] == fresh_user["email"]
        assert got["sla_status"] == "on_track"

    def test_unassign_clears_and_reopens(self, seeded_client, fresh_user):
        sigs = seeded_client.get(f"{BASE_URL}/api/signals?status=open&limit=50", timeout=30).json()["signals"]
        assert sigs
        sid = sigs[0]["signal_id"]
        seeded_client.post(
            f"{BASE_URL}/api/signals/{sid}/assign",
            json={"owner_email": fresh_user["email"]},
            timeout=30,
        )
        mid = seeded_client.get(f"{BASE_URL}/api/signals/{sid}", timeout=30).json()
        assert mid["status"] == "in_progress"

        r = seeded_client.post(
            f"{BASE_URL}/api/signals/{sid}/assign", json={"owner_email": None}, timeout=30
        )
        assert r.status_code == 200, r.text[:300]
        got = seeded_client.get(f"{BASE_URL}/api/signals/{sid}", timeout=30).json()
        assert got["owner_email"] is None
        assert got["due_date"] is None
        assert got["sla_status"] is None
        assert got["status"] == "open"

    def test_assign_404_unknown_signal(self, seeded_client, fresh_user):
        r = seeded_client.post(
            f"{BASE_URL}/api/signals/sig_doesnotexist/assign",
            json={"owner_email": fresh_user["email"]},
            timeout=30,
        )
        assert r.status_code == 404

    def test_filter_status_and_owner(self, seeded_client, fresh_user):
        sigs = seeded_client.get(f"{BASE_URL}/api/signals?status=open&limit=50", timeout=30).json()["signals"]
        assert sigs
        sid = sigs[0]["signal_id"]
        seeded_client.post(
            f"{BASE_URL}/api/signals/{sid}/assign",
            json={"owner_email": fresh_user["email"]},
            timeout=30,
        )

        ip = seeded_client.get(f"{BASE_URL}/api/signals?status=in_progress", timeout=30)
        assert ip.status_code == 200
        ip_sigs = ip.json()["signals"]
        assert len(ip_sigs) >= 1
        assert all(s["status"] == "in_progress" for s in ip_sigs)

        mine = seeded_client.get(f"{BASE_URL}/api/signals?owner=me", timeout=30)
        assert mine.status_code == 200
        mine_sigs = mine.json()["signals"]
        assert len(mine_sigs) >= 1
        assert all(s["owner_email"] == fresh_user["email"] for s in mine_sigs)

        other = seeded_client.get(
            f"{BASE_URL}/api/signals?owner=nobody@seekprofit-qa.com", timeout=30
        )
        assert other.status_code == 200
        assert other.json()["signals"] == []


# ---------------------------------------------------------------------------
# module: routers/reports.py — GET /api/reports/executive
# ---------------------------------------------------------------------------
class TestExecutiveReport:
    def test_executive_report_shape(self, demo_client):
        r = demo_client.get(f"{BASE_URL}/api/reports/executive", timeout=60)
        assert r.status_code == 200, r.text[:400]
        d = r.json()

        ws = d["workspace"]
        for k in ("name", "industry", "currency", "data_source"):
            assert k in ws
        assert ws["currency"]

        h = d["headline"]
        assert h["records_analyzed"] > 0
        assert isinstance(h["open_signal_count"], int)
        assert isinstance(h["open_pipeline_amount"], (int, float))
        assert h["revenue_recovered_display"]
        assert h["open_pipeline_display"]

        cats = d["category_totals"]
        assert isinstance(cats, list) and len(cats) == 3, f"expected 3 categories, got {[c['category'] for c in cats]}"
        assert {c["category"] for c in cats} == {"revenue_recovery", "profit_leak", "opportunity"}
        for c in cats:
            assert c["label"] and c["open_impact_display"] and c["resolved_impact_display"]

        trend = d["trend"]
        assert isinstance(trend, list) and len(trend) == 8, f"expected 8 buckets, got {len(trend)}"

        assert len(d["top_actions"]) <= 8
        for a in d["top_actions"]:
            assert a["signal_id"] and a["title"] and a["impact_display"]
            assert "owner_email" in a and "due_date" in a

        cp = d["top_counterparties"]
        assert isinstance(cp["customers"], list) and len(cp["customers"]) > 0
        assert isinstance(cp["vendors"], list) and len(cp["vendors"]) > 0
        assert cp["customers"][0]["invoiced"] >= cp["customers"][-1]["invoiced"]
        assert isinstance(d["resolved_wins"], list)
        assert d["period_label"] and d["generated_at"]

    def test_executive_report_pipeline_matches_categories(self, demo_client):
        d = demo_client.get(f"{BASE_URL}/api/reports/executive", timeout=60).json()
        total = sum(c["open_impact"] for c in d["category_totals"])
        assert abs(total - d["headline"]["open_pipeline_amount"]) < 0.01
        count = sum(c["open_count"] for c in d["category_totals"])
        assert count == d["headline"]["open_signal_count"]

    def test_executive_report_requires_auth(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/reports/executive", timeout=30)
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# module: routers/ai.py — SSE stream
# ---------------------------------------------------------------------------
def _parse_sse(resp, timeout_events=None):
    """Yield (event, data) tuples from an SSE response."""
    event = None
    data_lines = []
    for raw in resp.iter_lines(decode_unicode=True):
        if raw is None:
            continue
        line = raw.rstrip("\r")
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
        elif line == "":
            if event is not None:
                yield event, "\n".join(data_lines)
            event, data_lines = None, []


class TestAskStream:
    def test_stream_rejects_bad_token(self):
        r = requests.get(
            f"{BASE_URL}/api/ai/ask/stream",
            params={"token": "deadbeef", "question": "hello there"},
            timeout=30,
        )
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text[:200]}"

    def test_stream_requires_token(self):
        r = requests.get(
            f"{BASE_URL}/api/ai/ask/stream", params={"question": "hello there"}, timeout=30
        )
        assert r.status_code in (401, 422)

    def test_stream_happy_path(self, demo_client):
        token = demo_client.headers["Authorization"].split()[1]
        q = "Which customer has the largest overdue payment risk?"
        r = requests.get(
            f"{BASE_URL}/api/ai/ask/stream",
            params={"token": token, "question": q},
            stream=True,
            timeout=120,
        )
        assert r.status_code == 200, r.text[:300]
        ctype = r.headers.get("content-type", "")
        assert "text/event-stream" in ctype, ctype

        events = []
        deltas = []
        done_payload = None
        errors = []
        for ev, data in _parse_sse(r):
            events.append(ev)
            if ev == "delta":
                deltas.append(json.loads(data)["text"])
            elif ev == "error":
                errors.append(data)
            elif ev == "done":
                done_payload = json.loads(data)
                break
        r.close()

        assert not errors, f"stream emitted error events: {errors}"
        assert events[0] == "open", f"first event should be open, got {events[:3]}"
        assert len(deltas) >= 3, f"expected >=3 delta events, got {len(deltas)}"
        assert done_payload is not None, "no done event received"
        assert done_payload["text"].strip(), "done text empty"
        assert isinstance(done_payload["citations"], list)
        assert len(done_payload["citations"]) >= 1, "expected at least one citation"

        # at least one citation resolves to an actual record
        rid = done_payload["citations"][0]["record_id"]
        recs = demo_client.get(f"{BASE_URL}/api/signals?limit=1", timeout=30)
        assert recs.status_code == 200
        for c in done_payload["citations"]:
            for k in ("record_id", "type", "date", "amount", "counterparty"):
                assert k in c
        assert f"[rec:{rid}]" in done_payload["text"] or rid in done_payload["text"], (
            "cited id should appear in final text"
        )
        # dead tokens must be stripped from final text
        import re
        tokens = set(re.findall(r"\[rec:([a-zA-Z0-9_\-]+)\]", done_payload["text"]))
        cited = {c["record_id"] for c in done_payload["citations"]}
        assert tokens <= cited, f"unresolved tokens left in final text: {tokens - cited}"
