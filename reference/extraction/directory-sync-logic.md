# Directory Sync Logic

How the original system syncs the company directory from Google Workspace for name resolution.

---

## Overview

The directory sync fetches all employees from the Google Workspace People API, filters to the relevant domain, and stores structured data for the agent's name resolution.

---

## Implementation

```python
def sync_directory(domain_filter="company.com"):
    """Fetch all domain employees from Google Workspace."""
    
    people = people_api.listDirectoryPeople(
        sources=["DIRECTORY_SOURCE_TYPE_DOMAIN_PROFILE"],
        readMask="names,emailAddresses,organizations",
        pageSize=500
    )  # Handle pagination — may need 200+ pages for large orgs
    
    employees = []
    for person in people:
        email = person.emailAddresses[0].value
        if not email.endswith(f"@{domain_filter}"):
            continue
        
        name = person.names[0]
        org = person.organizations[0] if person.organizations else {}
        
        employees.append({
            "name": name.displayName,
            "first_name": name.givenName,
            "last_name": name.familyName,
            "email": email,
            "title": org.get("title"),
            "department": org.get("department"),
            "location": org.get("location"),
        })
    
    return sorted(employees, key=lambda p: p["name"])
```

## Storage Format

```json
{
  "synced_at": "2026-03-28T12:00:00Z",
  "source": "Google Workspace People API",
  "filter": "company.com",
  "count": 290,
  "people": [
    {
      "name": "Amy Fieber",
      "first_name": "Amy",
      "last_name": "Fieber",
      "email": "afieber@company.com",
      "title": "Director of Product Marketing",
      "department": "Marketing",
      "location": null
    }
  ]
}
```

## Key Notes

- **Pagination**: Large orgs (5000+ in parent company) require extensive pagination. The original system uses `pageSize=500` with up to 200 pages.
- **Domain filtering**: The API returns the entire org (parent company + subsidiaries). Filter to the relevant domain to get meaningful results.
- **Staleness**: Sync weekly. Check file age before syncing — skip if < 7 days old (unless forced).
- **Name resolution hierarchy**: People knowledge base (rich, curated) > Directory (broad, structured) > Ask user.
