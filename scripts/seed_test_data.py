"""Insert a fake meeting row for local testing.

Usage (from repo root):
    python -m scripts.seed_test_data
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Must come after load_dotenv so DATABASE_URL is set
from app.storage.database import init_db, AsyncSessionLocal
from app.storage.models import Meeting


MEETING_ID = "test-meeting-001"


async def main() -> None:
    await init_db()

    async with AsyncSessionLocal() as session:
        existing = await session.get(Meeting, MEETING_ID)
        if existing:
            print(f"Meeting {MEETING_ID!r} already exists — skipping insert.")
        else:
            session.add(Meeting(
                id=MEETING_ID,
                title="Andrew - Project Planning",
                date=datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0),
                participants=["Andrew Nee", "Sarah Chen"],
                duration_seconds=1800,
                processed=False,
            ))
            await session.commit()
            print(f"Inserted meeting {MEETING_ID!r}.")

    transcript_path = Path("data/transcripts") / f"{MEETING_ID}.json"
    if transcript_path.exists():
        print(f"Transcript already exists at {transcript_path} — skipping.")
    else:
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript = [
            {"timestamp": "00:00:09", "speaker": "Sarah Chen",  "text": "Hey Andrew, glad we could sync. I want to make sure we're aligned on the plan before anyone starts building."},
            {"timestamp": "00:00:18", "speaker": "Andrew Nee",  "text": "Same. I read through the brief this morning. Core feature set looks clear. I think we need a data model doc before anyone touches code though."},
            {"timestamp": "00:00:31", "speaker": "Sarah Chen",  "text": "Totally agree. Andrew, can you own that? Just a one-pager — entities, relationships, key constraints. By Thursday so it unblocks the backend team."},
            {"timestamp": "00:00:43", "speaker": "Andrew Nee",  "text": "Yes, I'll write the data model doc and post it in the shared drive by Thursday."},
            {"timestamp": "00:00:52", "speaker": "Sarah Chen",  "text": "Perfect. So action item one for you: write and share the data model doc by Thursday. Got it."},
            {"timestamp": "00:01:04", "speaker": "Sarah Chen",  "text": "Next — repo setup. Monorepo okay with you? I want CI and branch protection in place before anyone starts committing."},
            {"timestamp": "00:01:14", "speaker": "Andrew Nee",  "text": "Monorepo works. I'll set up the repo with folder structure, CI config, and branch protection on main this week. I'll add you and Marcus as required reviewers."},
            {"timestamp": "00:01:28", "speaker": "Sarah Chen",  "text": "Great. So your second action item is to set up the GitHub repo with CI and branch protection by end of this week. Confirmed?"},
            {"timestamp": "00:01:36", "speaker": "Andrew Nee",  "text": "Confirmed, I'll have it done by Friday."},
            {"timestamp": "00:01:45", "speaker": "Sarah Chen",  "text": "Last thing — design team needs to be looped in early. Andrew, can you schedule a kickoff with them for next week and include the brief so they have context?"},
            {"timestamp": "00:01:57", "speaker": "Andrew Nee",  "text": "Yes, I'll send a calendar invite to the design team for early next week with the brief attached."},
            {"timestamp": "00:02:08", "speaker": "Sarah Chen",  "text": "So action item three for Andrew: schedule the design kickoff for next week and share the brief with them. That's everything — thanks Andrew."},
        ]
        transcript_path.write_text(
            json.dumps(transcript, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Created transcript at {transcript_path}.")

    print("Done.")


asyncio.run(main())
