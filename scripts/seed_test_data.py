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
            {"timestamp": "00:00:19", "speaker": "Andrew Nee",  "text": "Same. I read through the brief this morning. I think the core feature set is clear, but I want to nail down the data model before we write a line of code."},
            {"timestamp": "00:00:32", "speaker": "Sarah Chen",  "text": "Agreed. Can you own the data model doc? Just a one-pager — entities, relationships, and any constraints we know about. That'll unblock the backend work."},
            {"timestamp": "00:00:45", "speaker": "Andrew Nee",  "text": "Yes, I'll write that up and share it by Thursday. I'll put it in the shared drive under the project folder."},
            {"timestamp": "00:01:01", "speaker": "Sarah Chen",  "text": "Perfect. On the repo side — do we have a structure decided? Monorepo or separate frontend and backend repos?"},
            {"timestamp": "00:01:12", "speaker": "Andrew Nee",  "text": "I'd lean monorepo for now given the team size. Less overhead. I'll go ahead and set up the repo with the initial folder structure and CI config this week."},
            {"timestamp": "00:01:28", "speaker": "Sarah Chen",  "text": "Great. Make sure to add branch protection on main and require PR reviews before merge. We got burned on that last project."},
            {"timestamp": "00:01:38", "speaker": "Andrew Nee",  "text": "Will do — I'll configure branch protection and add you and Marcus as required reviewers when I set it up."},
            {"timestamp": "00:01:52", "speaker": "Sarah Chen",  "text": "One more thing — we should loop in the design team early so they're not a bottleneck later. Can you schedule a kickoff with them for next week?"},
            {"timestamp": "00:02:05", "speaker": "Andrew Nee",  "text": "On it. I'll send a calendar invite to the design team for early next week and include the brief so they have context going in."},
        ]
        transcript_path.write_text(
            json.dumps(transcript, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Created transcript at {transcript_path}.")

    print("Done.")


asyncio.run(main())
