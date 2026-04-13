from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import ActionItem as ActionItemData
from app.storage.models import ActionItem, Meeting, Recap


async def save_meeting(session: AsyncSession, meeting_dict: dict) -> Meeting:
    """Insert a Meeting row if it doesn't exist. Returns the Meeting object."""
    existing = await session.get(Meeting, meeting_dict["conference_id"])
    if existing:
        return existing
    meeting = Meeting(
        id=meeting_dict["conference_id"],
        title=meeting_dict.get("title"),
        date=meeting_dict.get("start_time").replace(tzinfo=None) if meeting_dict.get("start_time") else None,
        participants=meeting_dict.get("participants", []),
        duration_seconds=meeting_dict.get("duration_seconds"),
    )
    session.add(meeting)
    await session.commit()
    return meeting


async def get_unprocessed_meetings(session: AsyncSession) -> list[Meeting]:
    """Return all meetings not yet processed."""
    result = await session.execute(
        select(Meeting).where(Meeting.processed == False).order_by(Meeting.date)
    )
    return list(result.scalars().all())


async def save_recap(
    session: AsyncSession,
    meeting_id: str,
    summary: str,
    uncertainties: list[str],
) -> Recap:
    """Upsert an approved Recap row with approved_at set to now."""
    result = await session.execute(select(Recap).where(Recap.meeting_id == meeting_id))
    recap = result.scalar_one_or_none()
    if recap:
        recap.summary = summary
        recap.uncertainties = uncertainties
        recap.approved_at = datetime.utcnow()
    else:
        recap = Recap(
            meeting_id=meeting_id,
            summary=summary,
            uncertainties=uncertainties,
            approved_at=datetime.utcnow(),
        )
        session.add(recap)
    await session.commit()
    return recap


async def save_action_items(
    session: AsyncSession,
    meeting_id: str,
    action_items: list[ActionItemData],
) -> list[ActionItem]:
    """Insert one ActionItem row per item. Returns the inserted rows."""
    rows = [
        ActionItem(
            meeting_id=meeting_id,
            task=item.task,
            timestamp=item.timestamp,
            context=item.context,
        )
        for item in action_items
    ]
    session.add_all(rows)
    await session.commit()
    return rows


async def mark_meeting_processed(session: AsyncSession, meeting_id: str) -> None:
    """Set processed=True on the Meeting row."""
    meeting = await session.get(Meeting, meeting_id)
    if meeting:
        meeting.processed = True
        await session.commit()


async def update_task_id(
    session: AsyncSession, action_item_id: int, tasks_id: str
) -> None:
    """Store the Google Tasks ID on an ActionItem after a successful push."""
    item = await session.get(ActionItem, action_item_id)
    if item:
        item.tasks_id = tasks_id
        await session.commit()
