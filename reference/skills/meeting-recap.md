# Skill: Meeting Recap & Action Items

This is the agent's primary capability. It handles both jobs: generating recaps and extracting action items.

---

## Step 0: Triage (Large Backlogs)

When there are **10+ unprocessed meetings**, run triage before recapping. This prevents wasting time on meetings that don't need processing.

1. **Scan all unprocessed meetings** — read metadata (date, participants, title, transcript size).
2. **Cross-reference against existing recaps** — find meetings already recapped but not flagged.
3. **Categorize each into buckets:**
   - **SKIP — Already Summarized**: A recap exists. Just mark as processed.
   - **SKIP — No Transcript**: No real content. Mark processed.
   - **SKIP — Large Group Meeting**: 10+ participants, training series, all-hands. Skip unless user was presenting.
   - **SKIP — Duplicate**: Same meeting captured multiple times. Keep the longest.
   - **RECAP**: Real transcript, no recap exists, worth processing.
4. **Present the triage report** with counts per category and the RECAP list.
5. **Wait for user to approve** which to skip and which to recap.

---

## Step 1: Discover & Present Unprocessed Meetings

Query for meetings that have transcripts but no approved recaps.

Present to user:
```
You have N unprocessed meeting(s):

1. Sarah Chen - Q1 Revenue Review (2026-03-28)
2. Mike Torres - Roadmap Sync (2026-03-28)
...

Which would you like to recap?
```

If no unprocessed meetings: "All caught up — no unprocessed meetings."

If 5+ meetings: offer to group by narrative arc (Step 1N).

---

## Step 1N: Narrative Threading

The most valuable part of the system. Meetings don't happen in isolation — they form ongoing story arcs.

### When to use
- **Always** when processing 5+ meetings
- **Optionally** for single meetings that connect to recent history

### How it works
1. Read metadata/opening lines of each unprocessed transcript
2. Check for narrative connections:
   - Same person across multiple dates (weekly 1:1 arc)
   - Same topic across different people
   - Sequential meetings on same day (huddle → event → debrief)
   - Connections to recent recaps
3. Group into narrative chunks
4. Present chunks with suggested processing order
5. User approves grouping

### Processing a narrative chunk
1. Read all transcripts in the chunk
2. Present the narrative as a **story** — what happened, how it progressed, what the throughline is
3. Flag uncertainties ("Things to check")
4. Draft action items for the chunk as a batch
5. Wait for user corrections and approval, then save all recaps in the chunk

### Connecting to existing context
Even for single meetings, check recent recaps for connections:
- "This builds on the retention discussion from Tuesday's call with Sarah."
- "Last week Ezra mentioned they were exploring this — looks like they've decided to move forward."

---

## Step 2: Recap Selected Meeting

When the user selects a meeting:

1. **Read the full transcript**
2. **Load context** (people, terms) for corrections
3. **Check transcript size** — if 500+ entries, use Deep-Dive Workflow (Step 2D)
4. **Generate narrative summary** covering:
   - What was discussed (key topics, decisions)
   - Commitments or next steps mentioned
   - Important context or background
   - Connections to ongoing narrative threads
5. **Present with draft action items and "things to check"**:

```
## Recap: Sarah Chen - Q1 Revenue Review (2026-03-28)

{Narrative summary}

---

**Action items (for you):**
- [ ] Add retention initiative to Q2 planning doc ([14:35:22])

**Things to check:**
1. Was the Moderna non-renewal in Q4 or Q1?

Does this capture the meeting accurately?
```

6. **Wait for validation.** Incorporate corrections, then save.

---

## Step 2D: Deep-Dive Workflow (500+ Transcript Entries)

For large/dense meetings that can't be processed in a single pass.

### Process:
1. **Split** transcript into 3-5 time-based segments
2. **Analyze each segment** (can be parallelized) for:
   - Topics discussed
   - Key decisions or direction set
   - Advice/guidance given
   - Specific action items with context
   - Important background info
   - Notable quotes with timestamps
3. **Present high-level meeting map** — chronological chunk list with brief descriptions
4. **Chunk-by-chunk validation loop**:
   - Present detailed draft for each chunk
   - Wait for user notes/corrections/approval
   - Lock chunk, move to next
   - Accumulate action items and context updates
5. **Deduplicate action items** across all chunks
6. **Consolidate** — save final recap, update context files

---

## Step 3: Save Verified Recap

Once approved:

1. **Store the recap** with:
   - Title and metadata (date, source, participants)
   - Summary section (validated text)
   - Action Items section (approved items with timestamps)
   - Full transcript (immutable source data)

2. **Mark meeting as processed** (don't show again)

3. **Push action items to Google Tasks**

---

## Step 4: Action Item Guidelines

- **User-only**: Only extract tasks for the user
- **Bias by recency**: Fresh meetings → capture everything. Old meetings → "None" is common
- **Timestamp citations required**: Every item ends with `([HH:MM:SS])`
- **Rich context**: Include enough detail that the item makes sense standalone
- **Batch by chunk**: When processing narrative arcs, present items per chunk

---

## Step 5: Continue or Finish

After completing a meeting or chunk:
- More meetings? → "Saved. N more unprocessed. Want to recap another?"
- Processing chunks? → Move to next chunk automatically
- All done? → "All caught up."

### End-of-session context updates
1. Review new people/terms discovered during session
2. Propose knowledge base updates
3. Apply changes after user confirmation

---

## Guardrails

- **Never save without approval** — always validate with user first
- **User-only action items** — never extract tasks for other participants
- **Timestamp citations** — verify every action item has one before saving
- **Context corrections** — always load people/terms before generating recaps
- **Preserve transcripts** — never modify raw transcript data
- **Narrative threading is not optional** — for 5+ meetings, always look for connections
- **Deep-dive for large meetings** — 500+ entries MUST use chunked workflow
