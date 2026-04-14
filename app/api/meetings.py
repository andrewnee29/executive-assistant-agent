from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from google.oauth2.credentials import Credentials
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.google.meet import list_meetings as google_list_meetings, match_calendar_title
from app.storage.database import get_session
from app.storage.models import ActionItem, Meeting, Recap, TranscriptStore, UserCredentials
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


@router.post("/{meeting_id}/reset")
async def reset_meeting(meeting_id: str, session: AsyncSession = Depends(get_session)):
    meeting = await session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    meeting.processed = False
    await session.commit()
    return {"meeting_id": meeting_id, "processed": False}


class ActionItemToggle(BaseModel):
    done: bool


@router.patch("/{meeting_id}/action-items/{item_id}", response_model=ActionItemResponse)
async def toggle_action_item(
    meeting_id: str,
    item_id: int,
    body: ActionItemToggle,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ActionItem).where(ActionItem.id == item_id, ActionItem.meeting_id == meeting_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found.")
    item.done = body.done
    await session.commit()
    await session.refresh(item)
    return item


class TranscriptResponse(BaseModel):
    meeting_id: str
    entries: list[dict]

    class Config:
        from_attributes = True


@router.get("/{meeting_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(meeting_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(TranscriptStore).where(TranscriptStore.meeting_id == meeting_id)
    )
    ts = result.scalar_one_or_none()
    if not ts:
        raise HTTPException(status_code=404, detail="No transcript found for this meeting.")
    return TranscriptResponse(meeting_id=meeting_id, entries=ts.entries_json)


@router.get("/{meeting_id}/progress")
async def get_progress(meeting_id: str, session: AsyncSession = Depends(get_session)):
    meeting = await session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return {"meeting_id": meeting_id, "processing_state": meeting.processing_state}


_DEFAULT_TRANSCRIPT = [
    {"timestamp": "00:00:10", "speaker": "Andrew Nee", "text": "Let's kick off the project planning session. I'll own the backend API spec by end of week."},
    {"timestamp": "00:01:05", "speaker": "Sarah Chen", "text": "Sounds good. I'll handle the frontend mockups and have them ready by Thursday."},
    {"timestamp": "00:02:30", "speaker": "Andrew Nee", "text": "Can you also send me the design system tokens? I need those to finalize the API response shapes."},
    {"timestamp": "00:03:15", "speaker": "Sarah Chen", "text": "Yes, I'll send those over today."},
    {"timestamp": "00:04:00", "speaker": "Andrew Nee", "text": "Great. I also need to schedule a review with the stakeholders — I'll set that up for next Tuesday."},
    {"timestamp": "00:05:20", "speaker": "Sarah Chen", "text": "Make sure to include the PM on that invite."},
    {"timestamp": "00:06:10", "speaker": "Andrew Nee", "text": "Will do. I'll also write up the acceptance criteria for the first milestone before that meeting."},
    {"timestamp": "00:07:45", "speaker": "Sarah Chen", "text": "Perfect. Should we do a quick check-in on Friday to sync before stakeholders?"},
    {"timestamp": "00:08:30", "speaker": "Andrew Nee", "text": "Yes, let's do Friday at 2pm. I'll send the calendar invite."},
    {"timestamp": "00:09:50", "speaker": "Sarah Chen", "text": "Works for me. I think that covers everything for today."},
]


class SeedBody(BaseModel):
    meeting_id: str = "test-meeting-001"
    title: str = "Andrew - Project Planning"
    participants: list[str] = ["Andrew Nee", "Sarah Chen"]
    transcript: list[dict] | None = None


@router.post("/seed")
async def seed_test_meeting(body: SeedBody = None, session: AsyncSession = Depends(get_session)):
    body = body or SeedBody()
    meeting_id = body.meeting_id
    title = body.title

    # Upsert Meeting row
    result = await session.execute(select(Meeting).where(Meeting.id == meeting_id))
    row = result.scalar_one_or_none()
    if row is None:
        session.add(Meeting(
            id=meeting_id,
            title=title,
            date=datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
            participants=body.participants,
            duration_seconds=1800,
            processed=False,
        ))
    else:
        row.title = title
        row.participants = body.participants
    await session.commit()

    # Resolve transcript
    entries = body.transcript or _DEFAULT_TRANSCRIPT

    # Upsert TranscriptStore row
    result2 = await session.execute(
        select(TranscriptStore).where(TranscriptStore.meeting_id == meeting_id)
    )
    ts_row = result2.scalar_one_or_none()
    if ts_row:
        ts_row.entries_json = entries
    else:
        session.add(TranscriptStore(meeting_id=meeting_id, entries_json=entries))
    await session.commit()

    return {"meeting_id": meeting_id, "title": title, "transcript_entries_written": len(entries)}
