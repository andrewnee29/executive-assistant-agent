# Skill: Context Management (People & Terms)

The agent automatically loads and applies context corrections when processing any content. This is what separates a useful meeting agent from a generic transcription tool.

---

## Context Sources

### People Knowledge Base (primary — rich context)

Contains for each person:
- Name and correct spelling
- Role, title, relationships
- Common transcription error patterns
- Behavioral notes and preferences
- Meeting frequency and history

**Example entry:**
```
Amy Fieber — Director of Product Marketing. afieber@company.com. 
Reports to VP Marketing. Working on Q1 campaign launch.
Common transcription errors: "Phoebe", "Phoeber" → "Amy Fieber"
First encountered: 2026-01-15 meeting.
```

### Company Directory (fallback — broad coverage)

Synced from Google Workspace People API. Contains:
- All domain employees (name, email, title, department)
- Refreshed weekly

Use when a name isn't found in the people knowledge base.

### Terms Knowledge Base

Contains:
- Active projects and status
- Tools and platforms
- Acronyms and definitions
- Common transcription corrections

**Example entries:**
```
RFP Builder — Internal tool for generating media proposals. Active project.
LIFE — Ad serving/campaign management platform. (Note: may appear as "life" lowercase)
HCP — Healthcare Professional
"lovable cloud" → "Lovable Cloud" (capitalization correction)
```

---

## How to Apply Context

### Before processing any content:
1. Load all context sources (people, directory, terms)
2. Build correction mapping (misspelling → correct form)

### During recap generation:
1. Scan transcript for names — match against people + directory
2. Scan for terms — match against terms knowledge base
3. Apply corrections in output (never modify raw transcript)
4. Flag uncertain corrections for user review

### Name Resolution Hierarchy

When encountering an unfamiliar or garbled name:

1. **Check people knowledge base** — fuzzy match against known people
2. **Check company directory** — search all employees by name
3. **Consider context** — who is speaking? What team? A garbled name in a Marketing meeting is more likely a marketer
4. **Ask user to confirm** — present best candidate with context:
   - "Sarah mentioned 'latherin' — could that be Katherine B. (Director of Product Marketing)?"
5. **Flag unknown** — if no candidate in either source:
   - "I couldn't match 'latherin' to anyone. Do you know who this is?"

**Never silently substitute a name.** Always confirm with user when uncertain.

### New Person Discovery

When user confirms a name match for someone not in the people knowledge base:

> "Katherine B. isn't in your contacts yet. From the directory: Director of Product Marketing, kb@company.com. Want me to add her?"

If confirmed, add with available info. Enrich over time as they appear in more meetings.

### Title Drift Detection

If the directory differs from stored people data (e.g., directory says "VP" but people KB says "Director"):

> "The directory now lists Katherine as VP of Product Marketing — want me to update?"

Never auto-update — always confirm.

---

## Common Correction Patterns

| Voice Transcription | Correct Term | Type |
|---------------------|-------------|------|
| Phoebe, Phoeber | Amy Fieber | Name mishearing |
| lovable cloud | Lovable Cloud | Capitalization |
| suave | Swoop | Product name mishearing |
| carabiner | Karabiner | Tool name |

These patterns are learned over time as the system processes more meetings and receives corrections.

---

## Knowledge Base Growth

The system should get measurably smarter:

**Week 1**: Basic name corrections, initial project vocabulary
**Week 4**: Most regular contacts known, common transcription errors catalogued
**Week 12**: Deep relationship context, project history, organizational map emerging

### What triggers growth:
- New person appears in a meeting → propose addition
- User corrects a name → store the error pattern
- New project/tool mentioned → propose term addition
- Title changes detected → propose update
- Recurring topics → build project context

### What the user sees:
- "I notice you've been meeting with Sarah weekly about the retention initiative. Want me to track this as an ongoing project?"
- "Three new people appeared in your meetings this week. Here's what I found in the directory — want me to add them?"
