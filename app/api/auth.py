import base64
import hashlib
import os
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.database import get_session
from app.storage.models import UserCredentials

router = APIRouter()

_SCOPES = [
    "https://www.googleapis.com/auth/meetings.space.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/admin.directory.user.readonly",
    "https://www.googleapis.com/auth/tasks",
]

# state -> {"verifier": str}  — cleared on callback
_pkce_store: dict[str, dict] = {}


def _build_flow() -> Flow:
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": os.environ["GOOGLE_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                "redirect_uris": [os.environ["GOOGLE_REDIRECT_URI"]],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=_SCOPES,
        redirect_uri=os.environ["GOOGLE_REDIRECT_URI"],
    )


def _generate_pkce() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) using S256."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


@router.get("/login")
async def login():
    verifier, challenge = _generate_pkce()
    flow = _build_flow()
    auth_url, state = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        code_challenge=challenge,
        code_challenge_method="S256",
    )
    _pkce_store[state] = {"verifier": verifier}
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(
    code: str,
    state: str,
    session: AsyncSession = Depends(get_session),
):
    pkce = _pkce_store.pop(state, None)
    if pkce is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")

    flow = _build_flow()
    flow.fetch_token(code=code, code_verifier=pkce["verifier"])
    creds = flow.credentials

    creds_dict = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or []),
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }

    result = await session.execute(
        select(UserCredentials).where(UserCredentials.user_id == "default")
    )
    row = result.scalar_one_or_none()
    if row:
        row.credentials_json = creds_dict
        row.updated_at = datetime.utcnow()
    else:
        session.add(UserCredentials(user_id="default", credentials_json=creds_dict))
    await session.commit()

    return RedirectResponse(url="/")


@router.get("/logout")
async def logout(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(UserCredentials).where(UserCredentials.user_id == "default")
    )
    row = result.scalar_one_or_none()
    if row:
        await session.delete(row)
        await session.commit()
    return RedirectResponse(url="/")
