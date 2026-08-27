"""SeekProfit — FastAPI entry.

Wires up routers, CORS, MongoDB indexes, and health checks. All business logic
lives in the `core/`, `services/`, and `routers/` modules.
"""
from __future__ import annotations
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load env BEFORE any other imports that may read environment variables.
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from fastapi import FastAPI  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from core.db import get_db, close_client  # noqa: E402

# Routers
from routers.auth import router as auth_router  # noqa: E402
from routers.onboarding import router as onboarding_router  # noqa: E402
from routers.overview import router as overview_router  # noqa: E402
from routers.signals import router as signals_router  # noqa: E402
from routers.ai import router as ai_router  # noqa: E402
from routers.imports import router as imports_router  # noqa: E402
from routers.reports import router as reports_router  # noqa: E402


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("seekprofit")


app = FastAPI(title="SeekProfit API", version="1.0.0")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "seekprofit"}


# Mount routers
app.include_router(auth_router)
app.include_router(onboarding_router)
app.include_router(overview_router)
app.include_router(signals_router)
app.include_router(ai_router)
app.include_router(imports_router)
app.include_router(reports_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    db = get_db()
    await db.users.create_index("email", unique=True)
    await db.users.create_index("user_id", unique=True)
    await db.workspaces.create_index("workspace_id", unique=True)
    await db.workspaces.create_index("owner_user_id")
    await db.workspaces.create_index("invited_emails")
    await db.financial_records.create_index([("workspace_id", 1), ("record_id", 1)], unique=True)
    await db.financial_records.create_index([("workspace_id", 1), ("type", 1)])
    await db.signals.create_index([("workspace_id", 1), ("signal_id", 1)], unique=True)
    await db.signals.create_index([("workspace_id", 1), ("status", 1)])
    logger.info("SeekProfit indexes ready")


@app.on_event("shutdown")
async def on_shutdown():
    close_client()
