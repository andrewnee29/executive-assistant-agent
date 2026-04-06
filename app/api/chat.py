import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from google.oauth2.credentials import Credentials

from app.core.agent import handle_message
from app.storage.database import get_session
from app.storage.models import UserCredentials

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(UserCredentials).where(UserCredentials.user_id == "default")
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Visit /auth/login first.",
        )

    c = row.credentials_json
    credentials = Credentials(
        token=c["token"],
        refresh_token=c.get("refresh_token"),
        token_uri=c.get("token_uri"),
        client_id=c.get("client_id"),
        client_secret=c.get("client_secret"),
        scopes=c.get("scopes"),
    )

    reply = await handle_message(
        session=session,
        credentials=credentials,
        user_message=body.message,
        user_name=os.environ.get("USER_NAME", "the user"),
    )
    return ChatResponse(reply=reply)
