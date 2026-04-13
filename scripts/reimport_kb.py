"""Re-import people and terms from the agent system context files with full notes."""
import re
import sqlite3
import json

PEOPLE_MD = "/Users/cmgibson/IDE Files/agent-system/meeting-agent/context/people.md"
TERMS_MD = "/Users/cmgibson/IDE Files/agent-system/meeting-agent/context/terms.md"
DIRECTORY_JSON = "/Users/cmgibson/IDE Files/agent-system/meeting-agent/context/directory.json"
DB_PATH = "/Users/cmgibson/IDE Files/Andrew Nee Meeting Agent/executive-assistant-agent/data/app.db"

# Map section headers to team names
SECTION_TEAMS = {
    "Core": "Leadership",
    "Team": "Cross-Functional",
    "Platform Operations Team": "Platform Operations",
    "External / Adjacent": "External",
}


def parse_people(text: str) -> list[dict]:
    """Parse people.md into structured entries with full notes."""
    people = []
    current_team = "General"

    # Split into blocks starting with **Name**
    # First, find all section headers to track team
    lines = text.split('\n')
    i = 0
    current_block_lines = []
    current_name = None

    while i < len(lines):
        line = lines[i]

        # Detect section headers (## Team Name)
        section_match = re.match(r'^## (.+)', line)
        if section_match:
            # Save previous block
            if current_name:
                people.append(_build_person(current_name, current_block_lines, current_team))
            current_name = None
            current_block_lines = []
            section_name = section_match.group(1).strip()
            current_team = SECTION_TEAMS.get(section_name, section_name)
            i += 1
            continue

        # Detect person entry start
        person_match = re.match(r'^\*\*([A-Z][^*]+?)\*\*\s*[—–\-]', line)
        if person_match:
            # Save previous block
            if current_name:
                people.append(_build_person(current_name, current_block_lines, current_team))
            current_name = person_match.group(1).strip()
            current_block_lines = [line]
            i += 1
            continue

        # Continuation of current block
        if current_name:
            current_block_lines.append(line)

        i += 1

    # Save last block
    if current_name:
        people.append(_build_person(current_name, current_block_lines, current_team))

    return people


def _build_person(name: str, block_lines: list[str], team: str) -> dict:
    """Build a person dict from their block of text."""
    block = '\n'.join(block_lines)

    # Skip "Caedon" — that's the user
    if name == "Caedon":
        return None

    # Extract role (first phrase after em dash)
    role = None
    role_match = re.search(r'\*\*' + re.escape(name) + r'\*\*\s*[—–\-]\s*(.+?)(?:\.|,|\n)', block)
    if role_match:
        role = role_match.group(1).strip()
        if len(role) > 80:
            dot = role.find('.', 40)
            role = role[:dot] if dot > 0 else role[:80]

    # Extract email
    email = None
    email_match = re.search(r'`([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})`', block)
    if email_match:
        email = email_match.group(1)

    # Build aliases
    aliases = []
    parts = name.split()
    if len(parts) >= 2:
        aliases.append(parts[0])
        aliases.append(parts[0][0] + parts[-1][0])

    # Extract full notes — everything after the first line, cleaned up
    # Remove the name/role first line prefix, keep everything else
    notes_text = block
    # Remove the **Name** — Role prefix from the start
    notes_text = re.sub(r'^\*\*[^*]+\*\*\s*[—–\-]\s*', '', notes_text, count=1)
    # Clean up markdown formatting for readability
    notes_text = notes_text.strip()
    # Remove > blockquotes prefix
    notes_text = re.sub(r'^>\s*', '', notes_text, flags=re.MULTILINE)

    if not notes_text or len(notes_text) < 10:
        notes_text = None

    return {
        'name': name,
        'role': role,
        'team': team,
        'email': email,
        'aliases': json.dumps(aliases),
        'notes': notes_text,
    }


def parse_terms(text: str) -> list[dict]:
    """Parse terms.md into structured entries with full definitions."""
    terms = []
    current_category = "General"
    current_term = None
    current_lines = []

    for line in text.split('\n'):
        # Detect category headers
        cat_match = re.match(r'^## (.+)', line)
        if cat_match:
            if current_term:
                terms.append(_build_term(current_term, current_lines, current_category))
            current_term = None
            current_lines = []
            current_category = cat_match.group(1).strip()
            continue

        # Detect term entry
        term_match = re.match(r'^\*\*(.+?)\*\*\s*[—–\-]\s*(.+)', line)
        if term_match:
            if current_term:
                terms.append(_build_term(current_term, current_lines, current_category))
            current_term = term_match.group(1).strip()
            current_lines = [term_match.group(2).strip()]
            continue

        # Continuation lines (indented or starting with -)
        if current_term and line.strip():
            current_lines.append(line)

    if current_term:
        terms.append(_build_term(current_term, current_lines, current_category))

    return terms


def _build_term(term: str, lines: list[str], category: str) -> dict:
    full_def = '\n'.join(lines).strip()
    # Clean up markdown
    full_def = re.sub(r'^\s*[-*]\s*', '- ', full_def, flags=re.MULTILINE)
    return {
        'term': term,
        'definition': full_def,
        'category': category,
    }


def enrich_emails(conn):
    """Fill in missing emails from directory.json."""
    with open(DIRECTORY_JSON) as f:
        directory = json.load(f)

    lookup = {}
    entries = directory.get('people', directory) if isinstance(directory, dict) else directory
    for entry in entries:
        if isinstance(entry, dict):
            name = entry.get('name', '')
            email = entry.get('email', '')
            if name and email:
                lookup[name.lower()] = email
                parts = name.split()
                if len(parts) >= 2:
                    lookup[f'{parts[0]} {parts[-1]}'.lower()] = email

    c = conn.cursor()
    c.execute('SELECT id, name FROM people WHERE email IS NULL')
    missing = c.fetchall()
    updated = 0
    for pid, name in missing:
        email = lookup.get(name.lower())
        if not email:
            parts = name.split()
            if len(parts) >= 2:
                email = lookup.get(f'{parts[0]} {parts[-1]}'.lower())
        if email:
            c.execute('UPDATE people SET email = ? WHERE id = ?', (email, pid))
            updated += 1
    conn.commit()
    return updated


def main():
    with open(PEOPLE_MD, 'r') as f:
        people_text = f.read()
    with open(TERMS_MD, 'r') as f:
        terms_text = f.read()

    people = [p for p in parse_people(people_text) if p is not None]
    terms = parse_terms(terms_text)

    print(f"Parsed {len(people)} people, {len(terms)} terms")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("DELETE FROM people")
    c.execute("DELETE FROM terms")

    for p in people:
        c.execute(
            "INSERT INTO people (name, role, team, email, aliases, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (p['name'], p['role'], p['team'], p['email'], p['aliases'], p['notes'])
        )

    for t in terms:
        c.execute(
            "INSERT INTO terms (term, definition, category) VALUES (?, ?, ?)",
            (t['term'], t['definition'], t['category'])
        )

    conn.commit()

    # Enrich missing emails
    email_count = enrich_emails(conn)

    # Report
    c.execute("SELECT COUNT(*) FROM people")
    print(f"People: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM people WHERE notes IS NOT NULL AND LENGTH(notes) > 50")
    print(f"  with rich notes: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM people WHERE email IS NOT NULL")
    print(f"  with emails: {c.fetchone()[0]}")
    c.execute("SELECT DISTINCT team FROM people WHERE team IS NOT NULL ORDER BY team")
    teams = [r[0] for r in c.fetchall()]
    print(f"  teams: {teams}")
    c.execute("SELECT COUNT(*) FROM terms")
    print(f"Terms: {c.fetchone()[0]}")
    print(f"Emails enriched from directory: {email_count}")

    # Show sample
    c.execute("SELECT name, team, LENGTH(notes) FROM people WHERE notes IS NOT NULL ORDER BY LENGTH(notes) DESC LIMIT 5")
    print("\nRichest profiles:")
    for r in c.fetchall():
        print(f"  {r[0]:30s} | {r[1]:20s} | {r[2]} chars")

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
