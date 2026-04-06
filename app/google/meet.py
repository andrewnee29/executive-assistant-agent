from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


class MeetClient:
    """Fetches conference records and transcripts from the Google Meet REST API."""

    def __init__(self, credentials: Credentials):
        self.service = build("meet", "v2", credentials=credentials)

    def list_recent_conferences(self, since_hours: int = 24) -> list[dict]:
        """Return completed conference records from the last N hours."""
        since = (datetime.utcnow() - timedelta(hours=since_hours)).isoformat() + "Z"
        response = (
            self.service.conferenceRecords()
            .list(filter=f'start_time>="{since}"')
            .execute()
        )
        return response.get("conferenceRecords", [])

    def get_transcript_entries(self, conference_id: str) -> list[dict]:
        """Return all transcript entries for a conference. Returns [] if not ready."""
        transcripts = (
            self.service.conferenceRecords()
            .transcripts()
            .list(parent=f"conferenceRecords/{conference_id}")
            .execute()
        )
        entries = []
        for transcript in transcripts.get("transcripts", []):
            if transcript.get("state") != "FILE_GENERATED":
                continue
            result = (
                self.service.conferenceRecords()
                .transcripts()
                .entries()
                .list(parent=transcript["name"])
                .execute()
            )
            entries.extend(result.get("entries", []))
        return entries

    def get_participants(self, conference_id: str) -> list[dict]:
        """Return participant list for a conference."""
        response = (
            self.service.conferenceRecords()
            .participants()
            .list(parent=f"conferenceRecords/{conference_id}")
            .execute()
        )
        return response.get("participants", [])
