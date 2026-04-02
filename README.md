# Executive Assistant Agent

A cloud-hosted meeting intelligence agent that connects to Google Workspace, automatically discovers and transcribes meetings, generates narrative recaps, extracts action items, and continuously learns about the people and topics in your professional world.

## What This Repo Contains

This is a **specification and reference repo** — not a running application. It provides everything needed to build the Executive Assistant Agent as a standalone, production-ready system.

### For the builder

| File | Purpose |
|------|---------|
| `PRD.md` | **Start here.** Functional requirements, user flows, and acceptance criteria |
| `ARCHITECTURE-NOTES.md` | Decisions left to you, with context on what we tried and why |

### Reference materials (supplementary)

| Folder | Purpose |
|--------|---------|
| `reference/system-prompt.md` | The agent's personality, behavior contract, and core instructions |
| `reference/skills/` | Detailed logic for each capability (recap, context management) |
| `reference/extraction/` | How meeting discovery and transcript fetching works |
| `reference/examples/` | Real output samples — what good looks like |
| `reference/schemas/` | Data formats and naming conventions |

## Origin

This system has been running in production (locally, via CLI) since December 2025, processing 90+ meetings across 40+ people. The PRD and reference materials are extracted from that working system, translated from platform-specific primitives into platform-agnostic specifications.

The goal: rebuild this as a cloud service accessible via chat UI and optionally SMS/text, where any user can connect their Google account and get the full experience.
