from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.config import Settings, get_settings
from app.google.auth import build_auth_url, exchange_code_for_tokens

router = APIRouter()


@router.get("/login")
async def login(settings: Settings = Depends(get_settings)):
    """Redirect user to Google OAuth consent screen."""
    auth_url = build_auth_url(settings)
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def oauth_callback(code: str, settings: Settings = Depends(get_settings)):
    """Handle Google OAuth callback and exchange code for tokens."""
    tokens = await exchange_code_for_tokens(code, settings)
    # TODO: store tokens per user, redirect to chat UI
    return {"message": "Authenticated successfully", "tokens": tokens}


@router.post("/logout")
async def logout():
    # TODO: revoke tokens and clear session
    return {"message": "Logged out"}
