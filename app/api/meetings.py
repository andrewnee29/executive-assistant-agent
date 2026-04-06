from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.database import get_session
from app.storage.models import ActionItem, Meeting, Recap

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
