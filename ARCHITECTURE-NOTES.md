# Architecture Notes

Decisions that are yours to make, with context on what we tried, what worked, and what didn't.

---

## LLM Selection

The system must be **LLM-agnostic** — don't hard-code to any specific provider. The original system runs on Claude (Opus for complex reasoning, Haiku for simple tasks), but the architecture should support swapping models.

**What matters for model selection:**
- Recap generation needs strong narrative synthesis (not just bullet points)
- Context correction (name/term fixing) works fine with smaller models
- Deep-dive chunking (500+ transcript entries) benefits from large context windows
- Action item extraction needs good judgment about what's actionable vs. informational

---

## Storage & Data Model

**Your call entirely.** The original system uses flat markdown files on disk. For a cloud service, you'll need something more structured. Key entities to model:

| Entity | Notes |
|--------|-------|
| **Meetings** | Discovered meetings with metadata (date, participants, duration, calendar title, conference ID) |
| **Transcripts** | Raw transcript text, speaker-attributed, timestamped. Source of truth — never modify |
| **Recaps** | User-validated narrative summaries. One per meeting |
| **Action Items** | Extracted tasks with timestamps, linked to meetings. Status tracking (open/done) |
| **People** | Growing knowledge base — names, roles, relationships, transcription error patterns |
| **Terms** | Projects, acronyms, tools — organizational vocabulary that evolves |
| **Context History** | How people/terms docs change over time (the system learns) |

**Important**: Transcripts are immutable source data. Recaps are human-validated interpretations. Both must be stored and accessible — recaps for quick reference, transcripts for when you need to go back to what was actually said.

---

## Google Tasks Integration

Action items should flow into Google Tasks after user approval. Design decisions for you:

- One task list per meeting? Per project? One global list?
- How to handle deduplication (same action item surfaces in consecutive meetings)?
- Should completed tasks in Google Tasks sync back to the app?
- What metadata to include (meeting date, transcript timestamp reference)?

The Google Tasks API requires the `tasks` OAuth scope.

---

## Meeting Discovery Mechanism

**Goal**: Near-real-time discovery of completed meetings.

The original system polls Google Meet API every 5 minutes via a cron job. In a cloud service, you have more options:

- **Polling**: Simple, reliable. Google Meet API has no webhooks for conference records. The `conferenceRecords.list` endpoint with a time filter is the discovery mechanism.
- **Calendar webhooks**: Google Calendar supports push notifications (webhooks). You could watch for calendar events with video conferences and trigger transcript fetch when the event ends.
- **Hybrid**: Calendar webhooks for awareness, polling for transcript availability (transcripts aren't immediately available after a meeting ends — there's a delay).

**Key constraint**: Google Meet transcripts are only available when `state: FILE_GENERATED`. There's typically a 1-5 minute delay after a meeting ends before the transcript is ready. Your polling/retry logic needs to account for this.

---

## Transcript Source

**Primary**: Google Meet REST API — conference records, participants, transcript entries. This is the canonical source and covers most meetings.

**Fallback strategy is yours to decide.** The original system falls back to a local transcription app for meetings where Google Meet didn't capture a transcript. In a cloud service, you might:
- Accept manual transcript upload
- Integrate with a cloud transcription service (Whisper API, Deepgram, etc.)
- Simply skip meetings without transcripts

---

## Chat Interface

The primary interface is a **chat UI** — the user interacts with the agent conversationally, not through forms or dashboards. The agent presents meeting lists, recaps, and action items in the conversation flow. The user validates, corrects, and approves through the chat.

**Additionally**, the app should surface:
- A view of extracted action items / to-dos (with status)
- Meeting history with recaps
- The agent's growing knowledge base (people, terms)

These could be separate pages/views, or woven into the chat experience — your call.

**Optional**: SMS/text message access for on-the-go interaction (e.g., "What meetings do I have unprocessed?" or "Remind me what Ezra and I discussed on Tuesday").

---

## Authentication & Multi-User

**MVP**: Single-user. One person connects their Google account and uses the system.

**Moonshot**: Multi-user. Anyone can sign up, connect their Google account, and get their own isolated agent with its own people/terms context. Each user's data is fully separated.

The Google OAuth flow is the same either way — the multi-user version just needs per-user token storage and data isolation.

**Required OAuth scopes**:
- `https://www.googleapis.com/auth/meetings.space.readonly` — Meet conference records + transcripts
- `https://www.googleapis.com/auth/calendar.readonly` — Calendar events for title matching
- `https://www.googleapis.com/auth/directory.readonly` — Company directory for name resolution
- `https://www.googleapis.com/auth/tasks` — Google Tasks for action item push

---

## Context File Management

Context files (people, terms) are **managed by the AI, not the user**. The user rarely touches these directly. The agent:

1. Discovers new people in meetings and proposes adding them
2. Detects transcription error patterns and records corrections
3. Updates roles/titles when they change (e.g., directory says "VP" but people doc says "Director")
4. Learns new project names, acronyms, and vocabulary over time
5. Always asks the user before making changes — never auto-updates silently

**Push beyond what we have**: Since you'll be fully integrated with Google, you can:
- Auto-populate people entries from meeting participant lists + directory lookups
- Cross-reference Calendar event attendees with the people knowledge base
- Detect when someone new appears in a meeting and pre-fill their info from the directory
- Track meeting frequency per person (who does the user meet with most?)
- Build relationship graphs from co-attendance patterns

The context system should get smarter over time without the user having to manually curate it.

---

## Deep-Dive Workflow

Meetings with 500+ transcript entries (typically 40+ minutes) can't be processed in a single LLM pass — they lose detail and overwhelm context. The original system uses a chunked approach:

1. Split transcript into 3-5 time-based segments
2. Analyze each segment in parallel
3. Present a high-level meeting map to the user
4. Walk through each chunk for validation
5. Deduplicate action items across chunks
6. Consolidate into final recap

For a cloud service, this could be:
- Server-side parallel processing with progress updates in the chat
- Streaming chunks to the user as they're ready
- A progress indicator while the agent works through a long meeting

---

## What the Original System Got Right

These are the things that make the system genuinely useful, not just technically interesting:

1. **Narrative threading** — connecting meetings into story arcs, not treating each as isolated. "This builds on what you discussed with Ezra on Tuesday."
2. **User validation before saving** — the agent never saves a recap without the user approving it. This builds trust and catches errors.
3. **User-only action items** — only extracts tasks for the user, not for the other person. Unless the user has a follow-up ("remind X about Y").
4. **Context corrections** — "Phoebe" → "Amy Fieber" automatically, because voice transcription is bad and the system learns the patterns.
5. **Timestamp citations** — every action item links back to the exact moment in the transcript where it was discussed.
6. **Triage for backlogs** — when 10+ meetings pile up, the system triages first (skip stubs, skip already-summarized, skip large group meetings) before processing.
7. **End-of-session context updates** — after processing meetings, the system reviews what it learned and updates people/terms files.
