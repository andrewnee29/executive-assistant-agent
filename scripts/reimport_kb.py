"""Re-import people and terms from the agent system context files with better parsing."""
import re
import sqlite3
import json

PEOPLE_MD = "/Users/cmgibson/IDE Files/agent-system/meeting-agent/context/people.md"
TERMS_MD = "/Users/cmgibson/IDE Files/agent-system/meeting-agent/context/terms.md"
DB_PATH = "/Users/cmgibson/IDE Files/Andrew Nee Meeting Agent/executive-assistant-agent/data/app.db"


def parse_people(text: str) -> list[dict]:
    """Parse people.md into structured entries."""
    people = []
    # Match bold name + em dash + description blocks
    # Pattern: **Name** — Role/description. More text. `email@example.com`
    blocks = re.split(r'\n(?=\*\*[A-Z])', text)

    for block in blocks:
        # Extract name
        name_match = re.match(r'\*\*(.+?)\*\*', block)
        if not name_match:
            continue
        name = name_match.group(1).strip()

        # Skip section headers and notes
        if name in ('Onboarding status', 'Next', 'Evolution', 'Access unblocked'):
            continue

        rest = block[name_match.end():].strip()

        # Extract role (text after em dash up to first period or sentence break)
        role = None
        role_match = re.match(r'[—–\-]\s*(.+?)(?:\.|,|\n|$)', rest)
        if role_match:
            role = role_match.group(1).strip()
            # Clean up role - remove trailing fragments
            if len(role) > 100:
                role = role[:role.find('.', 50)] if '.' in role[50:] else role[:100]

        # Extract email
        email = None
        email_match = re.search(r'`([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})`', block)
        if email_match:
            email = email_match.group(1)

        # Extract aliases from transcription notes
        aliases = []
        alias_match = re.search(r'(?:transcription|Note:).*?"([^"]+)".*?(?:is|for)\s+(\w+)', block, re.IGNORECASE)

        # Common short names as aliases
        parts = name.split()
        if len(parts) >= 2:
            aliases.append(parts[0])  # First name
            if len(parts[0]) > 2:
                aliases.append(parts[0][0] + parts[-1][0])  # Initials

        # Skip "Caedon" entry since that's the user
        if name == "Caedon":
            continue

        people.append({
            'name': name,
            'role': role,
            'email': email,
            'aliases': json.dumps(aliases),
        })

    return people


def parse_terms(text: str) -> list[dict]:
    """Parse terms.md into structured entries."""
    terms = []
    current_category = "General"

    for line in text.split('\n'):
        # Detect category headers
        cat_match = re.match(r'^## (.+)', line)
        if cat_match:
            current_category = cat_match.group(1).strip()
            continue

        # Match term entries: **Term** — Definition
        term_match = re.match(r'\*\*(.+?)\*\*\s*[—–\-]\s*(.+)', line)
        if term_match:
            term_name = term_match.group(1).strip()
            definition = term_match.group(2).strip()

            # For multi-line definitions, the first line is usually enough
            # Clean up definition - cap at reasonable length
            if len(definition) > 500:
                # Find a good break point
                cut = definition.find('. ', 200)
                if cut > 0:
                    definition = definition[:cut + 1]
                else:
                    definition = definition[:500] + '...'

            terms.append({
                'term': term_name,
                'definition': definition,
                'category': current_category,
            })

    return terms


def main():
    # Read source files
    with open(PEOPLE_MD, 'r') as f:
        people_text = f.read()
    with open(TERMS_MD, 'r') as f:
        terms_text = f.read()

    people = parse_people(people_text)
    terms = parse_terms(terms_text)

    print(f"Parsed {len(people)} people, {len(terms)} terms")

    # Connect to DB
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Clear existing people and terms
    c.execute("DELETE FROM people")
    c.execute("DELETE FROM terms")

    # Insert people
    for p in people:
        c.execute(
            "INSERT INTO people (name, role, email, aliases) VALUES (?, ?, ?, ?)",
            (p['name'], p['role'], p['email'], p['aliases'])
        )

    # Insert terms
    for t in terms:
        c.execute(
            "INSERT INTO terms (term, definition, category) VALUES (?, ?, ?)",
            (t['term'], t['definition'], t['category'])
        )

    conn.commit()

    # Verify
    c.execute("SELECT COUNT(*) FROM people")
    print(f"People in DB: {c.fetchone()[0]}")
    c.execute("SELECT name, role, email FROM people WHERE email IS NOT NULL LIMIT 10")
    print("Sample people with emails:")
    for r in c.fetchall():
        print(f"  {r[0]} | {r[1]} | {r[2]}")

    c.execute("SELECT COUNT(*) FROM terms")
    print(f"\nTerms in DB: {c.fetchone()[0]}")
    c.execute("SELECT term, category FROM terms LIMIT 10")
    print("Sample terms:")
    for r in c.fetchall():
        print(f"  {r[0]} | {r[1]}")

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
