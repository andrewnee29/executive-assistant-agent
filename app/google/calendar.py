from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


class CalendarClient:
    """Fetches calendar events for meeting title matching and attendee lookup."""

    def __init__(self, credentials: Credentials):
        self.service = build("calendar", "v3", credentials=credentials)

    def get_event_for_conference(self, conference_id: str) -> dict | None:
        """Find the calendar event that matches a Meet conference ID."""
        events = (
            self.service.events()
            .list(
                calendarId="primary",
                q=conference_id,
                singleEvents=True,
            )
            .execute()
        )
        items = events.get("items", [])
        return items[0] if items else None

    def list_upcoming_events(self, max_results: int = 10) -> list[dict]:
        from datetime import datetime
        now = datetime.utcnow().isoformat() + "Z"
        events = (
            self.service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return events.get("items", [])
