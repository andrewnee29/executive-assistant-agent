import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context_manager import load_people, load_terms
from app.core.meeting_processor import ProcessedMeeting, process_meeting
from app.google.meet import fetch_transcript, match_calendar_title
from app.google.tasks import push_action_items
from app.storage.repositories.meetings import (
    get_unprocessed_meetings,
    mark_meeting_processed,
    save_action_items,
    save_recap,
)

# Temporary in-process session state: user_name -> last ProcessedMeeting + meeting_id
_pending: dict[str, tuple[str, ProcessedMeeting]] = {}


async def handle_message(
    session: AsyncSession,
    credentials,
    user_message: str,
    user_name: str = "the user",
) -> str:
    msg = user_message.lower()

    # ------------------------------------------------------------------ #
    # 1. List unprocessed meetings                                         #
    # ------------------------------------------------------------------ #
    if any(kw in msg for kw in ("what's new", "whats new", "unprocessed", "meetings")):
        meetings = await get_unprocessed_meetings(session)
        if not meetings:
            return "All caught up — no unprocessed meetings."
        lines = [f"You have {len(meetings)} unprocessed meeting(s):"]
        for i, m in enumerate(meetings, 1):
            date_str = m.date.strftime("%Y-%m-%d") if m.date else "unknown date"
            title = m.title or m.id
            lines.append(f"{i}. {title} ({date_str})")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # 2. Process a meeting by index                                        #
    # ------------------------------------------------------------------ #
    if "recap" in msg:
        match = re.search(r"\d+", msg)
        if not match:
            return "Which meeting? Try: recap 1"
        index = int(match.group()) - 1

        meetings = await get_unprocessed_meetings(session)
        if index < 0 or index >= len(meetings):
            return f"No meeting at position {index + 1}. You have {len(meetings)} unprocessed meeting(s)."

        meeting = meetings[index]
        transcript = fetch_transcript(credentials, meeting.id, transcript_json=meeting.transcript_json)
        if not transcript:
            return f"No transcript available yet for '{meeting.title or meeting.id}'. Try again in a few minutes."

        people = await load_people(session)
        terms = await load_terms(session)

        result = await process_meeting(
            transcript=transcript,
            meeting_title=meeting.title,
            people=people,
            terms=terms,
            user_name=user_name,
        )

        _pending[user_name] = (meeting.id, result)
        return _format_result(result)

    # ------------------------------------------------------------------ #
    # 3. Approve the last processed meeting                                #
    # ------------------------------------------------------------------ #
    if "approve" in msg:
        if user_name not in _pending:
            return "Nothing pending approval. Run a recap first."

        meeting_id, result = _pending.pop(user_name)
        await save_recap(session, meeting_id, result.summary, result.uncertainties)
        saved_items = await save_action_items(session, meeting_id, result.action_items)
        push_action_items(credentials, result.action_items, meeting_title=meeting_id)
        await mark_meeting_processed(session, meeting_id)

        return (
            f"Saved. {len(saved_items)} action item(s) pushed to Google Tasks."
        )

    # ------------------------------------------------------------------ #
    # 4. Fallback                                                          #
    # ------------------------------------------------------------------ #
    return "I can help you recap meetings. Try asking: what's new, recap 1, or approve."


def _format_result(result: ProcessedMeeting) -> str:
    lines = ["**Recap**", result.summary]

    if result.uncertainties:
        lines += ["", "**Uncertainties to review:**"]
        lines += [f"- {u}" for u in result.uncertainties]

    if result.action_items:
        lines += ["", "**Action items:**"]
        for item in result.action_items:
            lines.append(f"- [{item.timestamp}] {item.task}")
    else:
        lines += ["", "No action items found."]

    lines += ["", "Reply **approve** to save and push to Google Tasks."]
    return "\n".join(lines)
