# Meeting Extraction Logic

How the original system discovers meetings and fetches transcripts from Google Meet. This is pseudocode — adapt to your tech stack.

---

## Overview

The extraction pipeline has three phases:
1. **Discover** — find conference records from Google Meet API
2. **Enrich** — match calendar titles, fetch transcripts, resolve participants
3. **Store** — write transcript data to storage, deduplicate

---

## Phase 1: Discover

```python
def discover(window_start, window_end):
    """Find all completed meetings in the time window."""
    
    # Query Google Meet API
    filter = f'start_time>="{window_start}" AND start_time<="{window_end}"'
    records = meet_api.conferenceRecords.list(filter=filter, pageSize=100)
    
    # Process each record
    meetings = []
    space_map = {}  # Deduplicate by Meet space ID
    
    for record in records:
        # Skip in-progress meetings (no end time)
        if not record.endTime:
            continue
        
        conference_id = record.name  # e.g., "conferenceRecords/abc123"
        space_id = record.space
        duration = (record.endTime - record.startTime).seconds
        
        # Deduplicate: keep longest duration per space
        if space_id in space_map:
            if duration <= space_map[space_id].duration:
                continue
        
        space_map[space_id] = {
            conference_id, space_id, 
            start_time, end_time, duration
        }
    
    # Fetch participants for each unique meeting
    for meeting in space_map.values():
        participants = meet_api.conferenceRecords.participants.list(
            parent=meeting.conference_id
        )
        
        # Filter to signed-in users with display names
        meeting.participants = [
            {name: p.signedinUser.displayName, id: p.signedinUser.user}
            for p in participants 
            if p.signedinUser.displayName
        ]
        
        # Skip phantom meetings (< 2 participants)
        if len(meeting.participants) >= 2:
            meetings.append(meeting)
    
    return meetings
```

---

## Phase 2: Enrich

### Calendar Title Matching

```python
def match_calendar_title(meeting, calendar_events):
    """Find a calendar event that overlaps with the meeting time."""
    
    for event in calendar_events:
        # Skip non-meeting events
        if event.eventType in ("workingLocation", "focusTime", "outOfOffice"):
            continue
        
        # Check time overlap
        if meeting.start < event.end and meeting.end > event.start:
            return event.summary  # Calendar event title
    
    return None  # No match — use fallback title
```

### Transcript Fetching

```python
def fetch_transcript(conference_id, participants):
    """Fetch transcript entries from Google Meet API."""
    
    # Check if transcript exists
    transcripts = meet_api.conferenceRecords.transcripts.list(
        parent=conference_id
    )
    
    if not transcripts or transcripts[0].state != "FILE_GENERATED":
        return []  # No transcript available
    
    transcript_id = transcripts[0].name
    
    # Build participant ref → display name map
    ref_to_name = {p.participant_ref: p.name for p in participants}
    
    # Fetch all entries (paginated)
    entries = meet_api.conferenceRecords.transcripts.entries.list(
        parent=transcript_id, pageSize=100
    )  # Handle pagination
    
    result = []
    for entry in entries:
        speaker = ref_to_name.get(entry.participant, "Speaker")
        time = entry.startTime.to_local().format("HH:MM:SS")
        result.append({
            speaker: speaker,
            text: entry.text,
            time: time
        })
    
    return result
```

### Participant Extraction

```python
def extract_primary_person(participants, user_name):
    """Get the primary non-user participant for filing."""
    
    others = sorted(
        [p for p in participants if user_name.lower() not in p.name.lower()],
        key=lambda p: p.name
    )
    
    if not others:
        return "unknown", "Unknown"
    
    full_name = others[0].name
    slug = slugify(full_name.split()[0])  # First name, lowercased, alphanumeric only
    return slug, full_name
```

---

## Phase 3: Store

### Deduplication

Two layers of deduplication:
1. **By space ID** during discovery (keeps longest duration)
2. **By conference ID** against existing stored meetings (prevents re-extraction)

```python
def should_extract(meeting, existing_conference_ids):
    """Check if this meeting has already been extracted."""
    return meeting.conference_id not in existing_conference_ids
```

### Transcript Format

The final stored transcript format:

```markdown
# Transcript: Q1 Revenue Review

**Date**: 2026-03-28
**Source**: google-meet
**Conference ID**: conferenceRecords/abc123
**Attendees**: Sarah Chen, User Name

---

## Transcript

**[14:30:05] Sarah Chen**: Let me walk you through the Q1 numbers.

**[14:30:12] User Name**: Sure, go ahead.

**[14:30:15] Sarah Chen**: Revenue is up 12% quarter over quarter...
```

---

## Key Implementation Notes

- **Pagination**: Both conference records and transcript entries can be paginated. Always handle pagination (the original uses `--page-all` which fetches all pages).
- **Timezone**: Transcript timestamps come in UTC. Convert to the user's local timezone for display.
- **Rate limits**: Google Meet API has rate limits. The original system handles this with sequential calls and a 5-minute polling interval.
- **Conference ID format**: Always `conferenceRecords/{id}` — this is the unique identifier for deduplication.
- **Transcript availability delay**: Transcripts aren't immediately available after a meeting ends. There's typically a 1-5 minute delay. Your polling/retry logic should account for this.
