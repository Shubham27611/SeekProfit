"""Quantify internal-field-name leakage rate in AI answers."""
import requests
from conftest import BASE_URL
from test_grounding_kpi_only import _new_inr_workspace, _leaks

s = requests.Session()
s.headers.update({"Content-Type": "application/json"})
c = _new_inr_workspace(s, "probe_leak")
questions = [
    "How much has this business previously recovered?",
    "How much has this business previously recovered?",
    "Do we have any recovery history? Explain your reasoning.",
    "Is prior recovery data available for this business?",
    "Summarise recovery to date and what remains open.",
]
leaks = 0
for i, q in enumerate(questions, 1):
    r = c.post(f"{BASE_URL}/api/ai/ask", json={"question": q}, timeout=180)
    a = r.json()["answer"] if r.status_code == 200 else f"HTTP {r.status_code}"
    found = _leaks(a)
    if found:
        leaks += 1
    print(f"[{i}] leaks={found} :: {a[:260]}")
    print("-" * 70)
print(f"leak rate: {leaks}/{len(questions)}")
