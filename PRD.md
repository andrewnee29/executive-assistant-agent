# Executive Assistant Agent — Product Requirements Document

## Overview

The Executive Assistant Agent is a cloud-hosted AI meeting intelligence system. It connects to a user's Google Workspace account, automatically discovers meetings, fetches transcripts, generates narrative recaps, extracts action items (pushing them to Google Tasks), and continuously builds a knowledge base about the people and topics in the user's professional world.

The user interacts with the agent through a **chat interface** (web UI, optionally SMS/text). The agent is conversational — it presents information, asks for validation, and learns from corrections.

---

## User Personas

**Primary**: An executive or manager who has 5-15 meetings per day and needs to stay on top of decisions, action items, and relationship context without manually reviewing every conversation.

**Secondary**: Any knowledge worker who wants AI-assisted meeting intelligence with minimal setup — connect Google, start getting recaps.

---

## Core Requirements

### R1: Google Account Connection

The user connects their Google account via OAuth. The system requests the following scopes:

| Scope | Purpose |
|-------|---------|
| `meetings.space.readonly` | Discover conference records, fetch participants and transcript entries |
| `calendar.readonly` | Match meetings to calendar events for titles/context |
| `directory.readonly` | Look up colleagues by name, title, department, email |
| `tasks` | Push approved action items to Google Tasks |

**Acceptance criteria:**
- User completes OAuth flow and sees confirmation
- System can immediately discover recent meetings
- Token refresh is handled automatically (no re-auth for ongoing use)
- Credentials are stored securely (encrypted at rest)

---

### R2: Meeting Discovery

The system automatically discovers completed meetings from Google Meet in near-real-time.

**How it works:**
1. Query `conferenceRecords.list` with a time filter for the discovery window
2. For each conference record, fetch the participant list
3. Filter out phantom meetings (< 2 participants) and in-progress meetings (no end time)
4. Deduplicate by Meet space ID — keep the longest-duration record
5. Match against Google Calendar events to resolve meeting titles
6. Skip meetings that have already been processed

**Acceptance criteria:**
- New meetings appear in the system within 10 minutes of ending
- Meetings are correctly attributed with: date, participants, duration, calendar title
- Duplicate meetings are never shown to the user
- Discovery works for back-fill (user can request "last 7 days" or "last 30 days" on first connect)

---

### R3: Transcript Fetching

For each discovered meeting, fetch the full transcript from Google Meet.

**How it works:**
1. Check `conferenceRecords.transcripts.list` for the meeting
2. Only process transcripts with `state: FILE_GENERATED`
3. Fetch all transcript entries via `conferenceRecords.transcripts.entries.list` (paginated)
4. Map participant references to display names
5. Format as timestamped, speaker-attributed text

**Transcript format:**
```
[14:30:05] Sarah Chen: Let me walk you through the Q1 numbers.
[14:30:12] User: Sure, go ahead.
[14:30:15] Sarah Chen: Revenue is up 12% quarter over quarter...
```

**Acceptance criteria:**
- Transcripts are fetched with speaker names (not participant IDs)
- Timestamps are in local time
- Full transcript is stored as immutable source data
- Meetings without transcripts are flagged but not discarded

---

### R4: Meeting Recap (Core Feature)

The agent generates a narrative summary of each meeting, validates it with the user, and stores the approved version.

#### R4.1: Presenting Unprocessed Meetings

When the user opens the app or asks "what's new," the agent presents unprocessed meetings:

```
You have 3 unprocessed meetings:

1. Sarah Chen - Q1 Revenue Review (2026-03-28)
2. Mike Torres - Product Roadmap Sync (2026-03-28)
3. Team Standup (2026-03-28, 6 participants)

Which would you like to recap?
```

#### R4.2: Generating Recaps

When the user selects a meeting:

1. Load the transcript
2. Load context files (people, terms) for name/term corrections
3. Generate a **narrative summary** — not bullet points, but a readable account of what was discussed, what was decided, and what matters
4. Present the summary with draft action items and "things to check" (uncertainties)

```
## Recap: Sarah Chen - Q1 Revenue Review (2026-03-28)

Revenue is up 12% QoQ, driven primarily by the Pfizer expansion 
and three new self-serve accounts. Sarah flagged that churn in the 
mid-market segment offset some gains — two accounts (Moderna, BMS) 
didn't renew, both citing budget cuts. She's proposing a retention 
play: quarterly check-ins with at-risk accounts before renewal dates.

You discussed moving the retention initiative into Q2 planning and 
Sarah will draft the check-in cadence by Friday.

---

**Action items (for you):**
- [ ] Add retention initiative to Q2 planning doc ([14:35:22])
- [ ] Intro Sarah to the account management team re: check-in process ([14:38:10])

**Things to check:**
1. Was the Moderna non-renewal in Q4 or Q1? Transcript was ambiguous.

Does this capture the meeting accurately? I can adjust before saving.
```

#### R4.3: User Validation

- The user can correct, add to, or approve the recap
- Corrections are incorporated and the updated version is presented
- Nothing is saved until the user explicitly approves
- Action items can be added, removed, or modified during validation

#### R4.4: Saving and Processing

Once approved:
- Store the recap (summary + action items + full transcript)
- Mark the meeting as processed (don't show it again)
- Push approved action items to Google Tasks
- Update context files if new people/terms were discovered

**Acceptance criteria:**
- Recaps are narrative, not bullet lists
- Context corrections are applied (wrong names fixed, acronyms resolved)
- User must approve before anything is saved
- Every action item has a transcript timestamp citation
- Action items are pushed to Google Tasks after approval

---

### R5: Action Item Extraction

Action items are extracted **for the user only** — not for the other meeting participants. If someone else committed to something, it's only tracked if the user has a related follow-up.

**Rules:**
- Each action item must cite a transcript timestamp: `([14:35:22])`
- Bias toward capturing items for recent meetings (within 1-2 days)
- For older meetings (1+ weeks), most items may already be handled — "None" is valid
- Include enough context that the action item makes sense without reading the full recap

**Acceptance criteria:**
- Only user's action items are extracted
- Each item has a timestamp citation
- Items are pushed to Google Tasks on approval
- Items are visible in the app with open/done status
- User can mark items done in the app (syncs to Google Tasks)

---

### R6: Context Learning System

The agent maintains and grows a knowledge base about the user's professional world. This is **required** — it's what makes the agent useful beyond a generic transcription tool.

#### R6.1: People Knowledge Base

For every person the user meets with, the system should track:

| Field | Source | Example |
|-------|--------|---------|
| Name (correct spelling) | Directory + user corrections | "Amy Fieber" (not "Phoebe") |
| Title / Role | Directory API | "Director of Product Marketing" |
| Email | Directory API | `afieber@company.com` |
| Department | Directory API | "Marketing" |
| Relationship context | Accumulated from meetings | "Reports to VP Marketing. Works on Q1 campaign." |
| Transcription error patterns | Discovered during recaps | "Phoebe", "Phoeber" → "Amy Fieber" |
| Meeting frequency | Calculated | "Met 12 times in last 30 days" |
| First encountered | Timestamp | "First appeared in 2026-01-15 meeting" |

**Behavior:**
- When a new person appears in a meeting, check the company directory first
- Pre-fill what's available (name, title, email, department)
- Ask the user to confirm before adding: "I see a new person in your meeting — Sarah Chen (VP Engineering, schen@company.com from your directory). Want me to add her to your contacts?"
- When transcription errors are detected, record the pattern for future correction
- When title changes are detected (directory differs from stored), flag it

#### R6.2: Terms & Vocabulary Knowledge Base

Track organizational vocabulary:

| Category | Example |
|----------|---------|
| Active projects | "RFP Builder — internal tool for generating media proposals" |
| Tools & platforms | "LIFE — ad serving platform" |
| Acronyms | "HCP — Healthcare Professional" |
| Transcription corrections | "lovable cloud" → "Lovable Cloud" |

**Behavior:**
- When an unknown term appears, flag it: "I heard 'lorem' — is this a project name?"
- When the user corrects a term, store the correction pattern for future use
- Apply all corrections automatically in future recaps

#### R6.3: Learning Loop

After each recap session, the agent should:
1. Review what new people/terms were discovered
2. Propose updates to the knowledge base
3. Wait for user confirmation
4. Apply changes

The knowledge base should visibly grow over time. After 30 days of use, the agent should know every regular meeting participant, every active project, and every common transcription error.

**Acceptance criteria:**
- New people are auto-detected and proposed for addition
- Transcription corrections are applied automatically after first discovery
- Users can view and edit the knowledge base
- The system gets measurably better at name/term correction over time

---

### R7: Narrative Threading

When processing multiple meetings, the agent should connect them into story arcs — not treat each as isolated.

**When to use:**
- Always when processing 5+ meetings in a session
- Optionally for single meetings that connect to recent history

**How it works:**
1. Scan unprocessed meetings for narrative connections:
   - Same person across multiple dates (weekly 1:1 arc)
   - Same topic across different people (project discussed in multiple meetings)
   - Sequential meetings on the same day (pre-event → event → debrief)
2. Group connected meetings into narrative chunks
3. Present the chunks with suggested processing order
4. Process each chunk as a connected story, not isolated data points

**Example output:**
```
I see a narrative thread across 3 meetings this week:

**Retention Initiative Arc:**
1. Sarah Chen - Q1 Revenue Review (Mon) — where the retention idea originated
2. Mike Torres - Product Roadmap (Wed) — where you discussed product support for retention
3. Team Standup (Thu) — where you assigned the Q2 planning update

Want me to process these as a connected arc?
```

**Acceptance criteria:**
- Connected meetings are identified and grouped
- Story arcs reference previous meetings ("This builds on Tuesday's discussion with Sarah")
- User can override grouping
- Single meetings reference recent history when relevant

---

### R8: Triage for Backlogs

When 10+ meetings are unprocessed, the system triages before processing:

**Triage categories:**
- **SKIP — No Transcript**: Empty/stub meetings. Mark as processed.
- **SKIP — Large Group Meeting**: 10+ participants, all-hands, training series. Skip unless the user was presenting.
- **SKIP — Duplicate**: Same meeting captured multiple times. Keep the longest.
- **RECAP**: Real transcript, worth processing.

**Behavior:**
1. Scan all unprocessed meetings
2. Categorize into buckets
3. Present triage report with counts
4. Wait for user to approve skips
5. Process approved RECAP list

**Acceptance criteria:**
- Triage runs automatically when 10+ meetings are queued
- User approves which to skip before anything is marked
- Skipped meetings are marked as processed (don't reappear)

---

### R9: Deep-Dive Workflow (Large Meetings)

Meetings with 500+ transcript entries require chunked processing:

1. Split transcript into 3-5 time-based segments
2. Analyze segments (can be parallelized server-side)
3. Present high-level meeting map to user
4. Walk through each chunk for validation (sequential, user approves each)
5. After all chunks validated, present deduplicated action items
6. Consolidate into final recap

**Acceptance criteria:**
- Large meetings are automatically detected and routed to deep-dive
- User sees progress as chunks are processed
- Each chunk is individually validated
- Action items are deduplicated across chunks
- Final recap is cohesive (not just chunks stapled together)

---

### R10: Directory Sync

Periodically sync the company directory from Google Workspace for name resolution.

**How it works:**
1. Call `people.listDirectoryPeople` with `readMask: names,emailAddresses,organizations`
2. Filter to the user's domain (e.g., `@company.com`)
3. Store: display name, first/last name, email, title, department
4. Refresh weekly (or on-demand)

**Use cases:**
- Resolving garbled transcript names to real people
- Pre-filling people entries when new contacts appear
- Detecting title/role changes

**Acceptance criteria:**
- Directory syncs on first connection and weekly thereafter
- User can trigger manual refresh
- Directory data is used for name resolution in recaps
- Stale directory entries don't override user-curated people data

---

## Non-Functional Requirements

### NF1: Security
- OAuth tokens encrypted at rest
- Transcript data isolated per user (if multi-user)
- No transcript data shared with third parties beyond LLM provider
- User can delete all their data

### NF2: Performance
- Meeting discovery within 10 minutes of meeting end
- Recap generation < 30 seconds for standard meetings (< 500 entries)
- Deep-dive processing < 3 minutes for large meetings
- Chat responses < 5 seconds for non-generation queries

### NF3: Reliability
- Graceful handling of Google API rate limits
- Retry logic for transient failures
- No data loss if processing is interrupted mid-recap

---

## User Flows

### Flow 1: First-Time Setup
```
User → Opens app
     → "Connect your Google account to get started"
     → OAuth flow (Meet + Calendar + Directory + Tasks)
     → "Connected! Let me scan your recent meetings..."
     → Discovery runs for last 7 days
     → "Found 12 meetings from this week. Want to start recapping?"
```

### Flow 2: Daily Check-In
```
User → Opens app / sends "what's new"
     → "You have 3 unprocessed meetings today:
        1. Sarah Chen - Revenue Review
        2. Mike Torres - Roadmap Sync  
        3. Team Standup
        Which would you like to recap?"
     → User: "Start with Sarah"
     → Agent generates recap, presents for validation
     → User approves (with minor correction)
     → Recap saved, action items pushed to Google Tasks
     → "Saved. 2 action items added to your Google Tasks. 
        Ready for the next one?"
```

### Flow 3: Catching Up After Vacation
```
User → Opens app after 5 days off
     → "You have 23 unprocessed meetings. Let me triage first..."
     → Triage report: 5 stubs, 3 large group meetings, 15 to recap
     → User approves skips
     → Agent groups remaining 15 into narrative arcs
     → Processes arc by arc with user validation
```

### Flow 4: Action Item Check
```
User → "What action items do I have open?"
     → Agent lists open items grouped by meeting/date
     → User marks some as done
     → Status synced to Google Tasks
```

---

## Success Metrics

After 30 days of use, the system should:
- Process meetings with < 2 corrections needed per recap (context learning working)
- Have a people knowledge base covering 90%+ of regular meeting participants
- Surface action items that the user actually acts on (not noise)
- Reduce the user's "meeting catch-up" time by 50%+ vs. manual review
