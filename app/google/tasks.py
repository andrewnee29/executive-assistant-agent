from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


class TasksClient:
    """Pushes approved action items to Google Tasks."""

    def __init__(self, credentials: Credentials):
        self.service = build("tasks", "v1", credentials=credentials)

    def get_or_create_tasklist(self, title: str = "Executive Assistant") -> str:
        """Return the task list ID, creating it if it doesn't exist."""
        lists = self.service.tasklists().list().execute()
        for lst in lists.get("items", []):
            if lst["title"] == title:
                return lst["id"]
        new_list = self.service.tasklists().insert(body={"title": title}).execute()
        return new_list["id"]

    def create_task(
        self,
        tasklist_id: str,
        title: str,
        notes: str | None = None,
        due: str | None = None,
    ) -> dict:
        """Create a task. due should be an RFC 3339 timestamp string."""
        body = {"title": title}
        if notes:
            body["notes"] = notes
        if due:
            body["due"] = due
        return self.service.tasks().insert(tasklist=tasklist_id, body=body).execute()

    def complete_task(self, tasklist_id: str, task_id: str) -> dict:
        return self.service.tasks().patch(
            tasklist=tasklist_id,
            task=task_id,
            body={"status": "completed"},
        ).execute()
