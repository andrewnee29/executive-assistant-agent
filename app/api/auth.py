import json
import os
from datetime import datetime

from fastapi import APIRouter, Depends
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


@router.get("/login")
async def login():
    flow = _build_flow()
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(code: str, session: AsyncSession = Depends(get_session)):
    flow = _build_flow()
    flow.fetch_token(code=code)
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
