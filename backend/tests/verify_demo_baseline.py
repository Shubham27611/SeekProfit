"""Verify demo workspace baseline after the run."""
import requests
from conftest import BASE_URL, DEMO_EMAIL, DEMO_PASSWORD, auth_session

s = requests.Session()
s.headers.update({"Content-Type": "application/json"})
r = s.post(f"{BASE_URL}/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}, timeout=30)
c = auth_session(r.json()["token"])
sigs = c.get(f"{BASE_URL}/api/signals?limit=100", timeout=60).json()["signals"]
print("total signals:", len(sigs))
print("statuses:", {x["status"] for x in sigs})
print("owners:", {x.get("owner_email") for x in sigs})
ov = c.get(f"{BASE_URL}/api/overview", timeout=60).json()
print("currency:", ov["workspace"]["currency"])
print([(k["slug"], k["value_display"], k.get("hint")) for k in ov["kpis"]])
