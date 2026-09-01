"""ORCID sign-in and current-user dependencies.

There is deliberately no alternative login path: a form that accepts an ORCID
iD without authenticating it would let anyone post as any researcher, including
as a paper's author.
"""
import re
import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .models import User

router = APIRouter()

ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")


def normalize_orcid(raw: str) -> Optional[str]:
    """Accept '0000000218250097' or '0000-0002-1825-0097' (or a full URL); return dashed form."""
    s = raw.strip().upper().replace("HTTPS://ORCID.ORG/", "").replace("-", "")
    if len(s) != 16:
        return None
    dashed = f"{s[0:4]}-{s[4:8]}-{s[8:12]}-{s[12:16]}"
    return dashed if ORCID_RE.match(dashed) else None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return db.get(User, user_id)


def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Login required")
    return user


def _login_as(request: Request, db: Session, orcid: str, name: str) -> User:
    user = db.query(User).filter(User.orcid == orcid).one_or_none()
    if user is None:
        user = User(orcid=orcid, name=name or orcid)
        db.add(user)
        db.commit()
    elif name and user.name != name:
        user.name = name
        db.commit()
    request.session["user_id"] = user.id
    return user


@router.get("/auth/orcid/login")
def orcid_login(request: Request, next: str = "/"):
    if not config.ORCID_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="ORCID sign-in is not configured (set ORCID_CLIENT_ID / ORCID_CLIENT_SECRET). "
            "Register a free public API client at https://orcid.org/developer-tools.",
        )
    state = secrets.token_urlsafe(24)
    request.session["oauth_state"] = state
    # only ever bounce back to a relative path on our own frontend
    request.session["oauth_next"] = next if next.startswith("/") and not next.startswith("//") else "/"
    url = f"{config.ORCID_BASE}/oauth/authorize?" + urlencode({
        "client_id": config.ORCID_CLIENT_ID,
        "response_type": "code",
        "scope": "/authenticate",
        "redirect_uri": config.ORCID_REDIRECT_URI,
        "state": state,
    })
    return RedirectResponse(url)


@router.get("/auth/orcid/callback")
def orcid_callback(request: Request, code: str = "", state: str = "", db: Session = Depends(get_db)):
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    if state != request.session.pop("oauth_state", None):
        raise HTTPException(status_code=400, detail="OAuth state mismatch")
    resp = httpx.post(
        f"{config.ORCID_BASE}/oauth/token",
        data={
            "client_id": config.ORCID_CLIENT_ID,
            "client_secret": config.ORCID_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.ORCID_REDIRECT_URI,
        },
        headers={"Accept": "application/json"},
        timeout=15,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"ORCID token exchange failed: {resp.text[:300]}")
    data = resp.json()
    orcid = normalize_orcid(data.get("orcid", ""))
    if orcid is None:
        raise HTTPException(status_code=502, detail="ORCID response missing iD")
    _login_as(request, db, orcid, data.get("name") or orcid)
    return RedirectResponse(config.FRONTEND_URL + request.session.pop("oauth_next", "/"))


@router.post("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"logged_in": False}


def _auth_info() -> dict:
    return {"orcid_ready": bool(config.ORCID_CLIENT_ID)}


@router.get("/api/me")
def me(user: Optional[User] = Depends(get_current_user)):
    if user is None:
        return {"logged_in": False, **_auth_info()}
    # The user sees their own identity; other users never do.
    return {"logged_in": True, "name": user.name, "orcid": user.orcid, **_auth_info()}
