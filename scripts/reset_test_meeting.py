"""Reset test-meeting-001 to unprocessed so it shows up in the chat UI again.

Usage (from repo root):
    python -m scripts.reset_test_meeting
"""

import asyncio
from dotenv import load_dotenv

load_dotenv()

from app.storage.database import init_db, AsyncSessionLocal
from app.storage.models import Meeting

MEETING_ID = "test-meeting-001"


async def main() -> None:
    await init_db()
    async with AsyncSessionLocal() as session:
        meeting = await session.get(Meeting, MEETING_ID)
        if not meeting:
            print(f"Meeting {MEETING_ID!r} not found — run scripts/seed_test_data.py first.")
            return
        meeting.processed = False
        await session.commit()
        print(f"Reset {MEETING_ID!r} to processed=False.")


asyncio.run(main())
