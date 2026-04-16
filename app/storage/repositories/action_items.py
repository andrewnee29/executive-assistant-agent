from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.storage.database import get_session
from app.storage.models import ActionItem


class ActionItemRepository:
    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.session = session

    async def list_all(self, done: bool | None = None) -> list[ActionItem]:
        query = select(ActionItem).order_by(ActionItem.id.desc())
        if done is not None:
            query = query.where(ActionItem.done == done)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def toggle_done(self, item_id: int, done: bool) -> ActionItem | None:
        item = await self.session.get(ActionItem, item_id)
        if not item:
            return None
        item.done = done
        await self.session.commit()
        await self.session.refresh(item)
        return item
