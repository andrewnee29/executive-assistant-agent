#!/usr/bin/env python3
"""
Import meeting data from the agent-system into the executive assistant app's SQLite database.

Source: /Users/cmgibson/IDE Files/agent-system/meeting-agent/
Target: /Users/cmgibson/IDE Files/Andrew Nee Meeting Agent/executive-assistant-agent/data/app.db
"""

import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

# ---------- Paths ----------

AGENT_BASE = Path("/Users/cmgibson/IDE Files/agent-system/meeting-agent")
SUMMARIES_DIR = AGENT_BASE / "meetings" / "verified-summaries"
TRANSCRIPTS_DIR = AGENT_BASE / "meetings" / "transcripts"
PEOPLE_MD = AGENT_BASE / "context" / "people.md"
TERMS_MD = AGENT_BASE / "context" / "terms.md"
TASKS_DB = Path("/Users/cmgibson/IDE Files/agent-system/task-system/db/tasks.db")

APP_DB = Path("/Users/cmgibson/IDE Files/Andrew Nee Meeting Agent/executive-assistant-agent/data/app.db")


# ---------- Helpers ----------

def connect_app_db():
    conn = sqlite3.connect(str(APP_DB))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def clear_tables(conn):
    """Delete all rows except user_credentials."""
    tables = ["action_items", "recaps", "transcript_store", "meetings", "people", "terms"]
    for t in tables:
        conn.execute(f"DELETE FROM {t}")
    conn.commit()
    print("Cleared all tables (except user_credentials).")


# ---------- People ----------

def parse_people(path: Path) -> list[dict]:
    """Parse people.md into structured entries."""
    text = path.read_text(encoding="utf-8")
    entries = []

    # Match bold name + em-dash + role/description lines
    # Pattern: **Name** — Role description...  possibly with email `email@...`
    pattern = re.compile(
        r"^\*\*([^*]+)\*\*\s*—\s*(.+?)$",
        re.MULTILINE,
    )

    for m in pattern.finditer(text):
        name = m.group(1).strip()
        rest = m.group(2).strip()

        # Skip entries that are clearly not people (like "Caedon" self-ref with "You (the user)")
        # but include anyway since it's useful context

        # Extract email if present: `email@domain.com`
        email_match = re.search(r"`([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)`", rest)
        email = email_match.group(1) if email_match else None

        # Extract role: first sentence/clause up to period or first major detail
        role_text = rest
        # Cut at first period that's followed by a space (not in abbreviation)
        period_match = re.search(r"\.\s", role_text)
        if period_match:
            role_text = role_text[: period_match.start()]
        # Trim long roles
        if len(role_text) > 200:
            role_text = role_text[:200].rsplit(" ", 1)[0]

        # Detect aliases from "Note:" lines or parenthetical names
        aliases = []
        # Common transcription errors noted in parentheses
        alias_match = re.search(r'(?:Note|note):\s*"([^"]+)"\s*(?:in transcripts|not)', rest)
        if alias_match:
            aliases.append(alias_match.group(1))

        entries.append({
            "name": name,
            "role": role_text.strip().rstrip("."),
            "email": email,
            "aliases": aliases,
        })

    return entries


def import_people(conn):
    people = parse_people(PEOPLE_MD)
    # Prioritize people with roles and emails, then roles only
    # Take top ~50 (most important)
    count = 0
    for p in people:
        conn.execute(
            "INSERT INTO people (name, role, email, aliases) VALUES (?, ?, ?, ?)",
            (p["name"], p["role"], p["email"], json.dumps(p["aliases"])),
        )
        count += 1
    conn.commit()
    print(f"Imported {count} people.")
    return count


# ---------- Terms ----------

def parse_terms(path: Path) -> list[dict]:
    """Parse terms.md into structured entries."""
    text = path.read_text(encoding="utf-8")
    entries = []
    current_category = "General"

    for line in text.split("\n"):
        # Detect category headers
        cat_match = re.match(r"^##\s+(.+)", line)
        if cat_match:
            current_category = cat_match.group(1).strip()
            continue

        # Match bold term + em-dash + definition
        term_match = re.match(r"^\*\*([^*]+)\*\*\s*—\s*(.+)", line)
        if term_match:
            term_name = term_match.group(1).strip()
            definition = term_match.group(2).strip()
            # Truncate very long definitions
            if len(definition) > 1000:
                definition = definition[:1000].rsplit(" ", 1)[0] + "..."
            entries.append({
                "term": term_name,
                "definition": definition,
                "category": current_category,
            })

    return entries


def import_terms(conn):
    terms = parse_terms(TERMS_MD)
    count = 0
    for t in terms:
        conn.execute(
            "INSERT INTO terms (term, definition, category) VALUES (?, ?, ?)",
            (t["term"], t["definition"], t["category"]),
        )
        count += 1
    conn.commit()
    print(f"Imported {count} terms.")
    return count


# ---------- Transcript parsing ----------

def parse_transcript(path: Path) -> tuple[list[dict], int | None, list[str]]:
    """
    Parse a transcript markdown file. Handles two formats:

    Format A (old/slipbox): blocks separated by '---' lines with Speaker:/Timestamp: fields
    Format B (gemini): inline transcript with "00:00:00\\n  Speaker: text" blocks

    Returns:
        entries: list of {timestamp, speaker, text}
        duration_seconds: parsed from metadata if available
        attendees: list of attendee names from header
    """
    raw_text = path.read_text(encoding="utf-8")
    entries = []
    duration_seconds = None
    attendees = []

    # Extract attendees from header
    att_match = re.search(r"\*\*Attendees\*\*:\s*(.+)", raw_text)
    if att_match:
        attendees = [a.strip() for a in att_match.group(1).split(",")]

    # Extract duration from metadata
    dur_match = re.search(r"Total Duration:\s*(\d+)\s*mins?", raw_text)
    if dur_match:
        duration_seconds = int(dur_match.group(1)) * 60

    # Try Format A first: blocks with Speaker:/Timestamp: fields
    blocks = re.split(r"-{5,}", raw_text)
    for block in blocks:
        speaker_match = re.search(r"Speaker:\s*(.+)", block)
        ts_match = re.search(r"Timestamp:\s*(\S+)", block)

        if speaker_match and ts_match:
            speaker = speaker_match.group(1).strip()
            raw_ts = ts_match.group(1).strip()

            try:
                dt = datetime.fromisoformat(raw_ts)
                timestamp = dt.strftime("%H:%M:%S")
            except (ValueError, TypeError):
                timestamp = raw_ts

            lines = block.strip().split("\n")
            text_lines = []
            past_timestamp = False
            for line in lines:
                if past_timestamp:
                    stripped = line.strip()
                    if stripped:
                        text_lines.append(stripped)
                elif "Timestamp:" in line:
                    past_timestamp = True

            spoken_text = " ".join(text_lines)
            if spoken_text:
                entries.append({
                    "timestamp": timestamp,
                    "speaker": speaker,
                    "text": spoken_text,
                })

    if entries:
        return entries, duration_seconds, attendees

    # Try Format B: Gemini transcript blocks
    # Pattern: timestamp line "00:01:23" followed by "  Speaker Name: text"
    # Find the transcript section
    transcript_section = raw_text
    transcript_marker = re.search(r"(?:📖\s*Transcript|##\s*(?:Full\s+)?Transcript)", raw_text)
    if transcript_marker:
        transcript_section = raw_text[transcript_marker.end():]

    # Split by timestamp markers: lines that are just "HH:MM:SS"
    ts_blocks = re.split(r"\n(\d{2}:\d{2}:\d{2})\s*\n", transcript_section)

    # ts_blocks: [preamble, ts1, text1, ts2, text2, ...]
    if len(ts_blocks) >= 3:
        for i in range(1, len(ts_blocks) - 1, 2):
            timestamp = ts_blocks[i]
            block_text = ts_blocks[i + 1].strip()

            # Parse speaker segments within the block
            # Pattern: "Speaker Name: text" — may have multiple speakers in one block
            speaker_segments = re.split(r"(?:^|\s{2,})(\w[\w\s.'-]+?):\s", block_text)
            # speaker_segments: [pre, name1, text1, name2, text2, ...]
            if len(speaker_segments) >= 3:
                for j in range(1, len(speaker_segments) - 1, 2):
                    speaker = speaker_segments[j].strip()
                    text = speaker_segments[j + 1].strip()
                    # Clean up trailing whitespace artifacts
                    text = re.sub(r"\s{4,}", " ", text).strip()
                    if text and len(speaker) < 50:  # sanity check on speaker name length
                        entries.append({
                            "timestamp": timestamp,
                            "speaker": speaker,
                            "text": text,
                        })
            elif block_text:
                # No speaker detected, store as unknown
                entries.append({
                    "timestamp": timestamp,
                    "speaker": "Unknown",
                    "text": block_text,
                })

    # Format C: "Speaker Name [HH:MM:SS]: text" (one per line)
    if not entries:
        line_pattern = re.compile(
            r"^([A-Z][\w\s.'-]+?)\s*\[(\d{2}:\d{2}:\d{2})\]:\s*(.+)",
            re.MULTILINE,
        )
        for m in line_pattern.finditer(raw_text):
            entries.append({
                "timestamp": m.group(2),
                "speaker": m.group(1).strip(),
                "text": m.group(3).strip(),
            })

    # Format D: Granola format — "**[HH:MM:SS] Speaker**: text" or "**[HH:MM:SS] You**: text"
    if not entries:
        granola_pattern = re.compile(
            r"\*\*\[(\d{2}:\d{2}:\d{2})\]\s*([^*]+?)\*\*:\s*(.+?)(?=\*\*\[|\Z)",
            re.DOTALL,
        )
        for m in granola_pattern.finditer(raw_text):
            ts = m.group(1)
            speaker = m.group(2).strip()
            text = m.group(3).strip()
            # Skip Gemini Notes entries for now (handled separately below)
            if "Gemini Notes" in speaker:
                continue
            if text:
                entries.append({
                    "timestamp": ts,
                    "speaker": speaker if speaker != "You" else "Caedon Gibson",
                    "text": text[:5000],
                })

    # Format E: Gemini Notes blocks with [HH:MM:SS] timestamps (narrative summaries)
    if not entries:
        note_blocks = re.findall(
            r"\*\*\[(\d{2}:\d{2}:\d{2})\]\s*Gemini Notes\s*\(([^)]+)\)\*\*:\s*(.+?)(?=\*\*\[|\Z)",
            raw_text,
            re.DOTALL,
        )
        for ts, note_type, content in note_blocks:
            entries.append({
                "timestamp": ts,
                "speaker": f"Gemini ({note_type})",
                "text": content.strip()[:5000],
            })

    return entries, duration_seconds, attendees


# ---------- Meetings + Recaps + Transcripts ----------

def parse_summary_metadata(text: str) -> dict:
    """Extract metadata from a verified summary markdown file."""
    meta = {
        "title": None,
        "attendees": [],
        "duration_text": None,
    }

    # Title from first H1
    title_match = re.search(r"^#\s+(.+)", text, re.MULTILINE)
    if title_match:
        meta["title"] = title_match.group(1).strip()

    # Duration
    dur_match = re.search(r"\*\*Duration\*\*:\s*~?(\d+)\s*mins?", text)
    if not dur_match:
        dur_match = re.search(r"\*\*Time\*\*:.*?\|\s*\*\*Duration\*\*:\s*~?(\d+)\s*mins?", text)
    if dur_match:
        meta["duration_text"] = int(dur_match.group(1))

    # Attendees from markdown list under ## Attendees
    att_section = re.search(r"##\s*Attendees\s*\n((?:[-*]\s+.+\n?)+)", text)
    if att_section:
        for line in att_section.group(1).split("\n"):
            line = line.strip().lstrip("-*").strip()
            if line:
                # Extract just the name (before em-dash or parenthetical)
                name = re.split(r"\s*—\s*|\s*\(", line)[0]
                name = re.sub(r"\*\*(.+?)\*\*", r"\1", name).strip()
                if name:
                    meta["attendees"].append(name)

    return meta


def _build_transcript_index() -> dict[str, Path]:
    """Build an index of transcript files for faster lookup."""
    index = {}
    for f in TRANSCRIPTS_DIR.iterdir():
        if f.suffix == ".md":
            index[f.stem] = f
    return index


_TRANSCRIPT_INDEX: dict[str, Path] | None = None


def find_matching_transcript(summary_filename: str) -> Path | None:
    """Find a transcript file that matches the summary filename."""
    global _TRANSCRIPT_INDEX
    if _TRANSCRIPT_INDEX is None:
        _TRANSCRIPT_INDEX = _build_transcript_index()

    stem = Path(summary_filename).stem  # e.g. "2025-12-01-ezra"

    # Direct match
    if stem in _TRANSCRIPT_INDEX:
        return _TRANSCRIPT_INDEX[stem]

    # Extract date and key parts from summary stem
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)", stem)
    if not date_match:
        return None
    date_prefix = date_match.group(1)
    name_part = date_match.group(2)  # e.g. "ezra", "casey-ward", "maggie-daily-meeting"

    # Strategy 1: Summary stem is a prefix of transcript stem
    # e.g. "2025-12-01-ezra" matches "2025-12-01-ezra-w7-mon-eod-demo"
    candidates = []
    for tstem, tpath in _TRANSCRIPT_INDEX.items():
        if tstem.startswith(stem):
            candidates.append((tstem, tpath))

    if len(candidates) == 1:
        return candidates[0][1]
    elif len(candidates) > 1:
        # Multiple matches — return the first alphabetically
        candidates.sort()
        return candidates[0][1]

    # Strategy 2: Transcript stem is a prefix of summary stem
    # e.g. "2026-01-19-maggie" matches "2026-01-19-maggie-daily-meeting"
    for tstem, tpath in _TRANSCRIPT_INDEX.items():
        if stem.startswith(tstem) and tstem.startswith(date_prefix):
            return tpath

    # Strategy 3: Same date + first keyword match
    # e.g. "2026-02-03-casey-ward" matches "2026-02-03-casey-ai-automation-tools"
    name_keywords = name_part.split("-")
    first_keyword = name_keywords[0] if name_keywords else None
    if first_keyword and len(first_keyword) > 2:
        date_matches = []
        for tstem, tpath in _TRANSCRIPT_INDEX.items():
            if tstem.startswith(date_prefix) and first_keyword in tstem:
                date_matches.append((tstem, tpath))
        if len(date_matches) == 1:
            return date_matches[0][1]
        elif len(date_matches) > 1:
            date_matches.sort()
            return date_matches[0][1]

    return None


def import_meetings(conn):
    summary_files = sorted(SUMMARIES_DIR.glob("*.md"))
    meeting_count = 0
    recap_count = 0
    transcript_count = 0

    for sf in summary_files:
        try:
            text = sf.read_text(encoding="utf-8")
            filename = sf.name
            stem = sf.stem  # e.g. "2025-12-01-ezra"

            # Parse date from filename
            date_match = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)", stem)
            if not date_match:
                print(f"  Skipping {filename}: cannot parse date from filename")
                continue

            date_str = date_match.group(1)
            title_slug = date_match.group(2)
            meeting_id = stem
            meeting_date = datetime.strptime(date_str, "%Y-%m-%d")

            # Parse summary metadata
            meta = parse_summary_metadata(text)
            title = meta["title"] or title_slug.replace("-", " ").title()
            participants = meta["attendees"]

            # Try to get duration from summary or transcript
            duration_seconds = meta.get("duration_text")
            if duration_seconds:
                duration_seconds = duration_seconds * 60

            # Find matching transcript
            transcript_path = find_matching_transcript(filename)
            transcript_entries = []
            if transcript_path:
                try:
                    entries, t_duration, t_attendees = parse_transcript(transcript_path)
                    transcript_entries = entries
                    if not duration_seconds and t_duration:
                        duration_seconds = t_duration
                    if not participants and t_attendees:
                        participants = t_attendees
                except Exception as e:
                    print(f"  Warning: failed to parse transcript {transcript_path.name}: {e}")

            # Insert meeting
            conn.execute(
                """INSERT OR REPLACE INTO meetings
                   (id, title, date, participants, duration_seconds, processed, processing_state, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    meeting_id,
                    title,
                    meeting_date.isoformat(),
                    json.dumps(participants),
                    duration_seconds,
                    True,
                    json.dumps({"step": 4, "total_steps": 4, "label": "complete"}),
                    datetime.utcnow().isoformat(),
                ),
            )
            meeting_count += 1

            # Insert recap (the full summary text)
            conn.execute(
                """INSERT INTO recaps (meeting_id, summary, uncertainties, approved_at)
                   VALUES (?, ?, ?, ?)""",
                (
                    meeting_id,
                    text,
                    json.dumps([]),
                    meeting_date.isoformat(),
                ),
            )
            recap_count += 1

            # Insert transcript if found
            if transcript_entries:
                conn.execute(
                    """INSERT OR REPLACE INTO transcript_store (meeting_id, entries_json)
                       VALUES (?, ?)""",
                    (meeting_id, json.dumps(transcript_entries)),
                )
                transcript_count += 1

            if meeting_count % 25 == 0:
                print(f"  Imported {meeting_count} meetings...")

        except Exception as e:
            print(f"  Error processing {sf.name}: {e}")
            continue

    conn.commit()
    print(f"Imported {meeting_count} meetings, {recap_count} recaps, {transcript_count} transcripts.")
    return meeting_count, recap_count, transcript_count


# ---------- Action Items (from tasks.db) ----------

def import_action_items(conn):
    """Import tasks from the task-system that reference meetings."""
    if not TASKS_DB.exists():
        print("Tasks database not found, skipping action items.")
        return 0

    tasks_conn = sqlite3.connect(str(TASKS_DB))
    tasks_conn.row_factory = sqlite3.Row

    rows = tasks_conn.execute(
        "SELECT id, text, source_file, person, meeting_date, timestamp_citation, status FROM tasks WHERE source_file IS NOT NULL"
    ).fetchall()

    # Get set of meeting IDs we already imported
    existing_ids = {
        row[0]
        for row in conn.execute("SELECT id FROM meetings").fetchall()
    }

    count = 0
    for row in rows:
        source_file = row["source_file"]
        task_text = row["text"]
        timestamp = row["timestamp_citation"] or ""
        person = row["person"] or ""
        status = row["status"]

        # Derive meeting_id from source_file
        # source_file is like "2025-12-09-dylan-zipcodes-ai-tutorial.md" or "ezra" etc
        source_stem = source_file.replace(".md", "")

        # Try to find a matching meeting_id
        meeting_id = None
        if source_stem in existing_ids:
            meeting_id = source_stem
        else:
            # Try with meeting_date prefix
            meeting_date = row["meeting_date"]
            if meeting_date:
                candidate = f"{meeting_date}-{source_stem}"
                if candidate in existing_ids:
                    meeting_id = candidate
                else:
                    # Fuzzy: find any meeting_id that starts with that date and contains the source stem
                    for mid in existing_ids:
                        if mid.startswith(meeting_date) and source_stem in mid:
                            meeting_id = mid
                            break

        if not meeting_id:
            # Still try to match by partial
            for mid in existing_ids:
                if source_stem in mid:
                    meeting_id = mid
                    break

        if not meeting_id:
            continue  # Can't link this task to a meeting

        done = status == "done" or status == "completed"

        conn.execute(
            """INSERT INTO action_items (meeting_id, task, timestamp, context, done, tasks_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                meeting_id,
                task_text,
                timestamp,
                f"Assigned to: {person}" if person else None,
                done,
                str(row["id"]),
            ),
        )
        count += 1

    tasks_conn.close()
    conn.commit()
    print(f"Imported {count} action items from tasks.db.")
    return count


# ---------- Main ----------

def main():
    print("=" * 60)
    print("Agent Data Import Script")
    print("=" * 60)
    print(f"Target DB: {APP_DB}")
    print()

    if not APP_DB.exists():
        print(f"ERROR: Target database not found at {APP_DB}")
        return

    conn = connect_app_db()

    try:
        print("Step 0: Clearing existing data...")
        clear_tables(conn)
        print()

        print("Step 1: Importing people...")
        import_people(conn)
        print()

        print("Step 2: Importing terms...")
        import_terms(conn)
        print()

        print("Step 3: Importing meetings, recaps, and transcripts...")
        import_meetings(conn)
        print()

        print("Step 4: Importing action items from tasks.db...")
        import_action_items(conn)
        print()

        # Summary
        print("=" * 60)
        print("IMPORT COMPLETE — Final counts:")
        for table in ["people", "terms", "meetings", "recaps", "transcript_store", "action_items"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {count}")
        print("=" * 60)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
