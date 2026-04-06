from googleapiclient.discovery import build

from app.llm.base import ActionItem


def get_or_create_task_list(credentials, list_name: str) -> str:
    """Return the ID of the named task list, creating it if it doesn't exist."""
    service = build("tasks", "v1", credentials=credentials)
    lists = service.tasklists().list().execute()
    for lst in lists.get("items", []):
        if lst.get("title") == list_name:
            return lst["id"]
    created = service.tasklists().insert(body={"title": list_name}).execute()
    return created["id"]


def push_action_items(
    credentials,
    action_items: list[ActionItem],
    list_name: str = "Executive Assistant",
    meeting_title: str | None = None,
) -> list[str]:
    """Push each ActionItem to Google Tasks. Returns the list of created task IDs."""
    service = build("tasks", "v1", credentials=credentials)
    tasklist_id = get_or_create_task_list(credentials, list_name)

    title_line = f"Meeting: {meeting_title}\n" if meeting_title else ""
    created_ids = []

    for item in action_items:
        notes = f"{title_line}Timestamp: {item.timestamp}\n\n{item.context}"
        task = service.tasks().insert(
            tasklist=tasklist_id,
            body={"title": item.task, "notes": notes},
        ).execute()
        created_ids.append(task["id"])

    return created_ids
