from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.storage.database import get_session
from app.storage.models import Meeting, Transcript


class MeetingRepository:
    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.session = session

    async def list_all(self) -> list[Meeting]:
        result = await self.session.execute(
            select(Meeting).order_by(Meeting.started_at.desc())
        )
        return result.scalars().all()

    async def get_by_id(self, meeting_id: str) -> Meeting | None:
        return await self.session.get(Meeting, meeting_id)

    async def get_transcript(self, meeting_id: str) -> Transcript | None:
        result = await self.session.execute(
            select(Transcript).where(Transcript.meeting_id == meeting_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, meeting: Meeting) -> Meeting:
        self.session.add(meeting)
        await self.session.commit()
        await self.session.refresh(meeting)
        return meeting
