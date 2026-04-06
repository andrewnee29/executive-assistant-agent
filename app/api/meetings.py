from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from google.oauth2.credentials import Credentials
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.google.meet import list_meetings as google_list_meetings, match_calendar_title
from app.storage.database import get_session
from app.storage.models import ActionItem, Meeting, Recap, UserCredentials
from app.storage.repositories.meetings import save_meeting

router = APIRouter()


class MeetingSummary(BaseModel):
    id: str
    title: str | None
    date: datetime | None
    participants: list[str]
    duration_seconds: int | None
    processed: bool

    class Config:
        from_attributes = True


class RecapResponse(BaseModel):
    summary: str
    uncertainties: list[str]
    approved_at: datetime

    class Config:
        from_attributes = True


class ActionItemResponse(BaseModel):
    id: int
    task: str
    timestamp: str | None
    context: str | None
    done: bool

    class Config:
        from_attributes = True


@router.post("/discover")
async def discover_meetings(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(UserCredentials).where(UserCredentials.user_id == "default")
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=401, detail="Not authenticated. Visit /auth/login first.")

    c = row.credentials_json
    credentials = Credentials(
        token=c["token"],
        refresh_token=c.get("refresh_token"),
        token_uri=c.get("token_uri"),
        client_id=c.get("client_id"),
        client_secret=c.get("client_secret"),
        scopes=c.get("scopes"),
    )

    now = datetime.now(timezone.utc)
    meetings = google_list_meetings(credentials, now - timedelta(days=7), now)

    saved = 0
    for m in meetings:
        title = match_calendar_title(credentials, m["start_time"], m["end_time"])
        m["title"] = title
        await save_meeting(session, m)
        saved += 1

    return {"found": len(meetings), "saved": saved}


@router.get("", response_model=list[MeetingSummary])
async def list_meetings(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Meeting).order_by(Meeting.date.desc()))
    return result.scalars().all()


@router.get("/{meeting_id}/recap", response_model=RecapResponse)
async def get_recap(meeting_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Recap).where(Recap.meeting_id == meeting_id)
    )
    recap = result.scalar_one_or_none()
    if not recap:
        raise HTTPException(status_code=404, detail="No recap found for this meeting.")
    return recap


@router.get("/{meeting_id}/action-items", response_model=list[ActionItemResponse])
async def get_action_items(meeting_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(ActionItem).where(ActionItem.meeting_id == meeting_id)
    )
    return result.scalars().all()
