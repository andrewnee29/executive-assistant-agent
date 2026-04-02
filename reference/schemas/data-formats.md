# Data Formats & Naming Conventions

---

## Meeting Naming Convention

All meetings follow: `YYYY-MM-DD-{person}-{topic-slug}`

- `person`: First name of primary non-user participant, lowercased, alphanumeric only
- `topic-slug`: Calendar title slugified (lowercase, spaces→hyphens, special chars removed, max 50 chars)
- If no calendar match: `{person}-meeting`

**Examples:**
```
2026-03-28-sarah-q1-revenue-review
2026-03-28-mike-product-roadmap-sync
2026-03-28-team-standup
2026-03-20-maggie-github-prs
```

**Collision handling**: If filename already exists, append `-2`, `-3`, etc.

---

## Transcript Format

```markdown
# Transcript: {Calendar Title or "Person Meeting"}

**Date**: YYYY-MM-DD
**Source**: google-meet
**Conference ID**: conferenceRecords/{id}
**Attendees**: Person A, Person B, Person C

---

## Transcript

**[HH:MM:SS] Speaker Name**: Transcript text here.

**[HH:MM:SS] Other Speaker**: Response text here.
```

**Notes:**
- Timestamps are local time
- Speaker names come from Google Meet participant data
- One blank line between entries
- Conference ID is the deduplication key

---

## Recap Format

```markdown
# {Person} - {Topic}

**Date**: YYYY-MM-DD
**Source**: google-meet

## Summary

{Validated narrative summary — prose, not bullet points}

## Action Items

- [ ] Action item text with context ([HH:MM:SS])
- [ ] Another action item ([HH:MM:SS–HH:MM:SS])

## Transcript

{Full verbatim transcript — copied from the raw transcript}
```

**Notes:**
- Summary is validated by user before saving
- Action items always have timestamp citations
- Full transcript is included as source of truth
- "None" or empty is valid for Action Items section

---

## People Knowledge Base Format

```markdown
# People

## Core
**Name** — Role/title. Relationship context. Key projects. 
Common transcription errors: "error1", "error2" → "Correct Name"

## Team
**Name** — Role. Team context. (Note: transcription corrections)

## External
**Name** — Company/role. How encountered.
```

**Example:**
```markdown
## Core
**Sarah Chen** — VP Engineering. Weekly 1:1s. Leading Q1 migration project. 
Direct report to CTO. Common transcription errors: "Sara" → "Sarah Chen"

## Team  
**Amy Fieber** — Director of Product Marketing. afieber@company.com.
Working on Q1 campaign launch. (Note: "Phoebe" / "Phoeber" = Amy Fieber)
```

---

## Terms Knowledge Base Format

```markdown
# Terms & Projects

## Active Projects
**Project Name** — Description and current status

## Tools & Platforms
**Tool Name** — What it is and how it's used

## Acronyms
**ACRO** — Full meaning (context if ambiguous)

## Transcription Corrections
| Transcribed | Correct | Type |
|-------------|---------|------|
| error text | Correct Text | Category |
```

---

## Action Item Format

```
- [ ] {action description with enough context to act on} ([HH:MM:SS])
```

**Rules:**
- Checkbox format (`- [ ]` for open, `- [x]` for done)
- Timestamp citation required — parenthetical at end
- Context-rich — someone reading the item cold should understand what to do
- User-only — never for other meeting participants
