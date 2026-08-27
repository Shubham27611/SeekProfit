"""One-off cleanup: restore demo workspace signals touched by Stage-3 UI tests."""
import requests
from dotenv import dotenv_values

BASE = dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"].rstrip("/")
s = requests.Session()
tok = s.post(f"{BASE}/api/auth/login", json={"email": "cfo@demo.seekprofit.app", "password": "demo1234"}, timeout=30).json()["token"]
s.headers.update({"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})

sigs = s.get(f"{BASE}/api/signals?limit=200", timeout=30).json()["signals"]
for sig in sigs:
    sid = sig["signal_id"]
    if sig.get("owner_email"):
        s.post(f"{BASE}/api/signals/{sid}/assign", json={"owner_email": None}, timeout=30)
        print("unassigned", sid)
    if sig["status"] in ("resolved", "dismissed"):
        print("closed signal (left as-is or reopened):", sid, sig["status"], sig["title"])

print("done")
