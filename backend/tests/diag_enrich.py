"""Diagnostic: time /api/signals/enrich locally vs via public ingress."""
import time
import uuid

import requests

PUB = "https://financial-core-9.preview.emergentagent.com"
LOC = "http://localhost:8001"

email = f"enrich_{uuid.uuid4().hex[:8]}@seekprofit-qa.com"
r = requests.post(f"{LOC}/api/auth/register", json={"email": email, "password": "Testpass123"}, timeout=30)
tok = r.json()["token"]
h = {"Authorization": f"Bearer {tok}"}
r = requests.post(f"{LOC}/api/workspace/setup",
                  json={"business_name": "TEST Enrich", "industry": "saas", "load_demo_data": True},
                  headers=h, timeout=120)
print("setup:", r.status_code, r.json().get("seeded_records"))
n_sig = requests.get(f"{LOC}/api/workspace/me", headers=h, timeout=30).json()["counts"]["signals"]
print("signals:", n_sig)

t0 = time.time()
r = requests.post(f"{LOC}/api/signals/enrich", headers=h, timeout=600)
print(f"LOCAL enrich: {r.status_code} in {time.time()-t0:.1f}s -> {r.text[:200]}")

t0 = time.time()
r = requests.post(f"{LOC}/api/signals/enrich", headers=h, timeout=600)
print(f"LOCAL enrich #2 (idempotency): {r.status_code} in {time.time()-t0:.1f}s -> {r.text[:200]}")

# now a second fresh workspace, enrich through public ingress
email2 = f"enrich2_{uuid.uuid4().hex[:8]}@seekprofit-qa.com"
r = requests.post(f"{PUB}/api/auth/register", json={"email": email2, "password": "Testpass123"}, timeout=30)
tok2 = r.json()["token"]
h2 = {"Authorization": f"Bearer {tok2}"}
requests.post(f"{PUB}/api/workspace/setup",
              json={"business_name": "TEST Enrich2", "industry": "saas", "load_demo_data": True},
              headers=h2, timeout=120)
t0 = time.time()
try:
    r = requests.post(f"{PUB}/api/signals/enrich", headers=h2, timeout=600)
    print(f"PUBLIC enrich: {r.status_code} in {time.time()-t0:.1f}s -> {r.text[:200]}")
except Exception as e:
    print(f"PUBLIC enrich exception after {time.time()-t0:.1f}s: {e}")
