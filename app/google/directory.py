from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


class DirectoryClient:
    """Looks up people in the Google Workspace directory for name/role resolution."""

    def __init__(self, credentials: Credentials):
        self.service = build("admin", "directory_v1", credentials=credentials)

    def lookup_person(self, email: str) -> dict | None:
        """Fetch a directory entry by email address."""
        try:
            return self.service.users().get(userKey=email).execute()
        except Exception:
            return None

    def search_people(self, query: str) -> list[dict]:
        """Search the directory by name or email fragment."""
        result = self.service.users().list(
            customer="my_customer",
            query=query,
            maxResults=10,
        ).execute()
        return result.get("users", [])
