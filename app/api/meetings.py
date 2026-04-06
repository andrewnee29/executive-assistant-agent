from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.storage.repositories.meetings import MeetingRepository

router = APIRouter()


@router.get("/")
async def list_meetings(repo: MeetingRepository = Depends()):
    """List all discovered meetings."""
    return await repo.list_all()


@router.get("/{meeting_id}")
async def get_meeting(meeting_id: str, repo: MeetingRepository = Depends()):
    """Get a single meeting with its recap and transcript."""
    meeting = await repo.get_by_id(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.get("/{meeting_id}/transcript")
async def get_transcript(meeting_id: str, repo: MeetingRepository = Depends()):
    """Get the raw transcript for a meeting."""
    transcript = await repo.get_transcript(meeting_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript


@router.post("/{meeting_id}/recap")
async def approve_recap(meeting_id: str, recap: dict):
    """User approves and saves the agent-generated recap."""
    # TODO: validate and persist
    return {"status": "saved", "meeting_id": meeting_id}
