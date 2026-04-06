from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Literal

from app.storage.repositories.action_items import ActionItemRepository

router = APIRouter()


class ActionItemUpdate(BaseModel):
    status: Literal["open", "done"]


@router.get("/")
async def list_action_items(
    status: str | None = None,
    repo: ActionItemRepository = Depends(),
):
    """List action items, optionally filtered by status."""
    return await repo.list_all(status=status)


@router.patch("/{item_id}")
async def update_action_item(
    item_id: str,
    update: ActionItemUpdate,
    repo: ActionItemRepository = Depends(),
):
    """Update the status of an action item."""
    item = await repo.update_status(item_id, update.status)
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")
    return item


@router.post("/{item_id}/push-to-tasks")
async def push_to_google_tasks(item_id: str):
    """Push an approved action item to Google Tasks."""
    # TODO: call google.tasks integration
    return {"status": "pushed", "item_id": item_id}
