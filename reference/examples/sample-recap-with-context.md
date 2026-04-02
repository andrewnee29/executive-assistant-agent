# Example Recap — Meeting With Rich Context

This example shows how the agent uses context to correct names, apply terminology, and connect to narrative threads.

---

# Ezra — Best Meeting Debrief & Data Hub Reveal

**Date**: 2026-03-18
**Source**: meet-extract

## Summary

Brief post-mortem after Best Meeting of the Week. Quick and positive — "This was even more fun than Lorem, being able to pass it off and just let people run with it." Max blew people away. Konrad (CEO) had a blast. Maggie got flooded with Slack messages ("What do I do with all these messages?" — "You just respond to them.").

Ezra pivots to demoing **Data Hub** — a Hatch feature that accepts SQL queries, CSVs, REST APIs, or file uploads, runs profiling, and generates an Install button that opens Claude Code and auto-installs itself as the MCP connector. This directly solves the plugin CLI installation problem from Mar 16. Caedon: "This is directly where I want to go. Tell everyone else you can only upload CSVs. No. I want direct BigQuery."

Demo hit a bug (.env file issue — Ezra fixed live). Cut short because Ezra had a call with Max.

Key quote from Ezra: "The stuff that we're doing where you're manually going into Claude Desktop and doing stuff, we can circumvent completely through our tools."

## Action Items

None — Data Hub exploration will happen naturally once it's live.

---

### What the agent did here (commentary for the builder):

1. **Context corrections applied**: "Konrad" correctly identified as CEO (from people knowledge base). "Hatch", "Lorem", "Data Hub" all recognized as internal projects (from terms knowledge base).
2. **Narrative connection**: "This directly solves the plugin CLI installation problem from Mar 16" — the agent connected this meeting to a previous discussion, showing continuity.
3. **Key quotes preserved**: Direct quotes with attribution make the recap feel authentic and useful.
4. **"None" for action items**: The agent correctly judged that no action items were needed — this was informational, not action-oriented. This is a valid and important judgment call.
5. **Tone**: Reads like a brief from a colleague who was in the room, not a mechanical transcript summary.
