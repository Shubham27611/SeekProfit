"""Shared fixtures for SeekProfit backend tests."""
import os
import uuid

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
_base = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not _base:
    raise RuntimeError("REACT_APP_BACKEND_URL missing from env and /app/frontend/.env")
BASE_URL = _base.rstrip("/")

DEMO_EMAIL = "cfo@demo.seekprofit.app"
DEMO_PASSWORD = "demo1234"


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="class")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="class")
def fresh_user(api_client):
    """Register a brand-new user; returns dict(token, user, email, password)."""
    email = f"test_{uuid.uuid4().hex[:10]}@seekprofit-qa.com"
    password = "Testpass123"
    r = api_client.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": password, "name": "TEST User"},
        timeout=30,
    )
    if r.status_code != 200:
        pytest.fail(f"register failed {r.status_code}: {r.text[:400]}")
    data = r.json()
    return {"token": data["token"], "user": data["user"], "email": email, "password": password}


def auth_session(token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="class")
def seeded_client(fresh_user):
    """Fresh user with demo dataset seeded via /api/workspace/setup."""
    s = auth_session(fresh_user["token"])
    r = s.post(
        f"{BASE_URL}/api/workspace/setup",
        json={
            "business_name": "TEST Acme Co",
            "industry": "saas",
            "currency": "USD",
            "load_demo_data": True,
        },
        timeout=90,
    )
    if r.status_code != 200:
        pytest.fail(f"workspace setup failed {r.status_code}: {r.text[:400]}")
    return s


@pytest.fixture(scope="class")
def demo_client(api_client):
    """Session for the pre-existing demo account."""
    r = api_client.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
        timeout=30,
    )
    if r.status_code != 200:
        pytest.fail(f"demo login failed {r.status_code}: {r.text[:400]}")
    return auth_session(r.json()["token"])
