"""Ad-hoc probe: does the AI report the 12% baseline KPI as actually-recovered money?"""
import uuid
import requests
from conftest import BASE_URL, auth_session
from test_currency_grounding import INR_CSV

email = f"probe_{uuid.uuid4().hex[:8]}@seekprofit.app"
r = requests.post(f"{BASE_URL}/api/auth/register",
                  json={"email": email, "password": "testpass123", "name": "Probe"}, timeout=30)
tok = r.json()["token"]
s = auth_session(tok)
s.post(f"{BASE_URL}/api/workspace/setup",
       json={"business_name": "Probe Co", "industry": "saas", "currency": "USD",
             "load_demo_data": False}, timeout=90)
up = requests.Session()
up.headers.update({"Authorization": f"Bearer {tok}"})
print("csv:", up.post(f"{BASE_URL}/api/imports/csv",
                      files={"file": ("t.csv", INR_CSV.encode(), "text/csv")}, timeout=120).json())
ov = s.get(f"{BASE_URL}/api/overview", timeout=60).json()
print("KPIs:", [(k["slug"], k["value_display"], k.get("hint")) for k in ov["kpis"]])
for q in ["How much revenue have we recovered so far?",
          "Summarise our recovery performance to date."]:
    a = s.post(f"{BASE_URL}/api/ai/ask", json={"question": q}, timeout=180).json()
    print("\nQ:", q)
    print("A:", a["answer"])
