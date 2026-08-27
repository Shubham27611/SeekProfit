"""Auth routes — JWT email/password + Emergent Google callback."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from core.db import get_db
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)
    name: Optional[str] = None


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class GoogleCallbackInput(BaseModel):
    session_id: str


class TokenResponse(BaseModel):
    token: str
    user: dict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_workspace_doc(owner_user_id: str, name: str = "My Workspace") -> dict:
    return {
        "workspace_id": f"ws_{uuid.uuid4().hex[:12]}",
        "owner_user_id": owner_user_id,
        "name": name,
        "industry": None,
        "currency": "USD",
        "is_seeded": False,
        "invited_emails": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def _find_workspace_for(user: dict) -> Optional[dict]:
    """Return the workspace this user has access to (owned OR invited)."""
    db = get_db()
    ws = None
    if user.get("workspace_id"):
        ws = await db.workspaces.find_one({"workspace_id": user["workspace_id"]}, {"_id": 0})
    if not ws:
        ws = await db.workspaces.find_one(
            {"$or": [
                {"owner_user_id": user["user_id"]},
                {"invited_emails": user["email"]},
            ]},
            {"_id": 0},
        )
    return ws


async def _ensure_workspace(user: dict) -> dict:
    """Ensure the user has a workspace. Creates one on first sign-in."""
    db = get_db()
    ws = await _find_workspace_for(user)
    if ws is None:
        ws = _new_workspace_doc(user["user_id"])
        await db.workspaces.insert_one(dict(ws))
    if user.get("workspace_id") != ws["workspace_id"]:
        await db.users.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"workspace_id": ws["workspace_id"]}},
        )
        user["workspace_id"] = ws["workspace_id"]
    return ws


def _sanitized(user: dict, workspace: dict | None) -> dict:
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user.get("name") or user["email"].split("@")[0],
        "picture": user.get("picture"),
        "auth_provider": user.get("auth_provider", "email"),
        "workspace": {
            "workspace_id": workspace["workspace_id"],
            "name": workspace.get("name") or "My Workspace",
            "is_seeded": bool(workspace.get("is_seeded")),
            "industry": workspace.get("industry"),
            "currency": workspace.get("currency", "USD"),
        } if workspace else None,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register", response_model=TokenResponse)
async def register(payload: RegisterInput):
    db = get_db()
    email = payload.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user_id = f"user_{uuid.uuid4().hex[:12]}"
    doc = {
        "user_id": user_id,
        "email": email,
        "name": (payload.name or email.split("@")[0]).strip(),
        "password_hash": hash_password(payload.password),
        "picture": None,
        "auth_provider": "email",
        "workspace_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(dict(doc))
    ws = await _ensure_workspace(doc)
    token = create_access_token(user_id, email)
    return {"token": token, "user": _sanitized(doc, ws)}


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginInput):
    db = get_db()
    email = payload.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    ws = await _ensure_workspace(user)
    token = create_access_token(user["user_id"], user["email"])
    return {"token": token, "user": _sanitized(user, ws)}


@router.post("/google/callback", response_model=TokenResponse)
async def google_callback(payload: GoogleCallbackInput):
    """Exchange an Emergent Auth session_id for a SeekProfit JWT."""
    db = get_db()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": payload.session_id},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Google sign-in failed. Please try again.")
    data = resp.json()
    email = (data.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Google returned no email.")

    existing = await db.users.find_one({"email": email})
    now = datetime.now(timezone.utc).isoformat()
    if existing:
        # Upsert picture/name, mark provider.
        provider = existing.get("auth_provider", "email")
        if existing.get("password_hash"):
            provider = "both" if provider != "google" else "both"
        else:
            provider = "google"
        await db.users.update_one(
            {"user_id": existing["user_id"]},
            {"$set": {
                "name": data.get("name") or existing.get("name"),
                "picture": data.get("picture") or existing.get("picture"),
                "auth_provider": provider,
                "last_login_at": now,
            }},
        )
        user = await db.users.find_one({"user_id": existing["user_id"]})
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        doc = {
            "user_id": user_id,
            "email": email,
            "name": data.get("name") or email.split("@")[0],
            "picture": data.get("picture"),
            "password_hash": None,
            "auth_provider": "google",
            "workspace_id": None,
            "created_at": now,
            "last_login_at": now,
        }
        await db.users.insert_one(dict(doc))
        user = doc

    ws = await _ensure_workspace(user)
    token = create_access_token(user["user_id"], user["email"])
    return {"token": token, "user": _sanitized(user, ws)}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    ws = await _find_workspace_for(current_user)
    return _sanitized(current_user, ws)


class InviteInput(BaseModel):
    email: EmailStr


@router.post("/invite")
async def invite(payload: InviteInput, current_user: dict = Depends(get_current_user)):
    """Lean invite: add the email to the workspace's invited_emails list.
    Whoever signs in with that email later will join this workspace."""
    db = get_db()
    ws = await _find_workspace_for(current_user)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    if ws["owner_user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Only the workspace owner can invite.")
    email = payload.email.lower().strip()
    await db.workspaces.update_one(
        {"workspace_id": ws["workspace_id"]},
        {"$addToSet": {"invited_emails": email}},
    )
    return {"ok": True, "invited_email": email}
