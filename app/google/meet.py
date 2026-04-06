from datetime import datetime, timezone

from googleapiclient.discovery import build

from app.llm.base import TranscriptEntry

# Non-meeting event types to skip when searching calendar
_SKIP_EVENT_TYPES = {"focusTime", "outOfOffice", "workingLocation"}


def list_meetings(credentials, window_start: datetime, window_end: datetime) -> list[dict]:
    """Return completed, multi-participant meetings in the given time window.

    Deduplicates by Meet space ID, keeping the longest-duration record.

    Each returned dict has:
        conference_id, space_id, start_time, end_time,
        duration_seconds, participants (list of display name strings)
    """
    meet = build("meet", "v2", credentials=credentials)

    start_str = _to_rfc3339(window_start)
    end_str = _to_rfc3339(window_end)
    time_filter = f'start_time>="{start_str}" AND start_time<="{end_str}"'

    records = _paginate(
        meet.conferenceRecords().list,
        list_key="conferenceRecords",
        filter=time_filter,
    )

    # Filter and enrich each record
    candidates: list[dict] = []
    for rec in records:
        # Skip meetings still in progress
        if not rec.get("endTime"):
            continue

        conference_id = rec["name"].split("/")[-1]
        space_id = rec.get("space", "").split("/")[-1]

        start_time = _parse_dt(rec["startTime"])
        end_time = _parse_dt(rec["endTime"])
        duration = int((end_time - start_time).total_seconds())

        participants = _fetch_participant_names(meet, rec["name"])
        if len(participants) < 2:
            continue

        candidates.append({
            "conference_id": conference_id,
            "space_id": space_id,
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": duration,
            "participants": participants,
        })

    return _dedup_by_space(candidates)


def fetch_transcript(credentials, conference_id: str) -> list[TranscriptEntry]:
    """Return transcript entries for a conference, or [] if not yet available.

    Only reads transcripts with state FILE_GENERATED. Handles pagination.
    """
    meet = build("meet", "v2", credentials=credentials)
    parent = f"conferenceRecords/{conference_id}"

    transcripts = _paginate(
        meet.conferenceRecords().transcripts().list,
        list_key="transcripts",
        parent=parent,
    )

    entries: list[TranscriptEntry] = []
    for transcript in transcripts:
        if transcript.get("state") != "FILE_GENERATED":
            continue

        raw_entries = _paginate(
            meet.conferenceRecords().transcripts().entries().list,
            list_key="entries",
            parent=transcript["name"],
        )

        for entry in raw_entries:
            participant_name = (
                entry.get("participant", {}).get("signedinUser", {}).get("displayName")
                or entry.get("participant", {}).get("anonymousUser", {}).get("displayName")
                or "Unknown"
            )
            entries.append(TranscriptEntry(
                timestamp=_format_offset(entry.get("startTime", "")),
                speaker=participant_name,
                text=entry.get("text", ""),
            ))

    return entries


def match_calendar_title(
    credentials, start_time: datetime, end_time: datetime
) -> str | None:
    """Return the calendar event title that overlaps this time window, or None.

    Skips non-meeting event types (focus time, OOO, working location).
    Returns the first match found.
    """
    calendar = build("calendar", "v3", credentials=credentials)

    result = (
        calendar.events()
        .list(
            calendarId="primary",
            timeMin=_to_rfc3339(start_time),
            timeMax=_to_rfc3339(end_time),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    for event in result.get("items", []):
        if event.get("eventType") in _SKIP_EVENT_TYPES:
            continue
        title = event.get("summary")
        if title:
            return title

    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _paginate(list_method, list_key: str, **kwargs) -> list[dict]:
    """Call a list method repeatedly until all pages are exhausted."""
    items = []
    page_token = None
    while True:
        response = list_method(**kwargs, pageToken=page_token).execute()
        items.extend(response.get(list_key, []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return items


def _fetch_participant_names(meet_service, record_name: str) -> list[str]:
    participants = _paginate(
        meet_service.conferenceRecords().participants().list,
        list_key="participants",
        parent=record_name,
    )
    names = []
    for p in participants:
        name = (
            p.get("signedinUser", {}).get("displayName")
            or p.get("anonymousUser", {}).get("displayName")
        )
        if name:
            names.append(name)
    return names


def _dedup_by_space(meetings: list[dict]) -> list[dict]:
    """Keep the longest-duration record per space ID."""
    best: dict[str, dict] = {}
    for m in meetings:
        sid = m["space_id"]
        if sid not in best or m["duration_seconds"] > best[sid]["duration_seconds"]:
            best[sid] = m
    return list(best.values())


def _to_rfc3339(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _format_offset(iso_timestamp: str) -> str:
    """Convert an ISO timestamp to HH:MM:SS for use as a transcript offset."""
    if not iso_timestamp:
        return "00:00:00"
    try:
        dt = _parse_dt(iso_timestamp)
        return dt.strftime("%H:%M:%S")
    except ValueError:
        return iso_timestamp
