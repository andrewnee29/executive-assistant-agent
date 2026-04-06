from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.storage.database import get_session
from app.storage.models import ActionItem


class ActionItemRepository:
    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.session = session

    async def list_all(self, status: str | None = None) -> list[ActionItem]:
        query = select(ActionItem).order_by(ActionItem.created_at.desc())
        if status:
            query = query.where(ActionItem.status == status)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_status(self, item_id: str, status: str) -> ActionItem | None:
        item = await self.session.get(ActionItem, item_id)
        if not item:
            return None
        item.status = status
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def save(self, item: ActionItem) -> ActionItem:
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item
