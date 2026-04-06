from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import PersonEntry, TermEntry
from app.storage.models import Person, Term


async def load_people(session: AsyncSession) -> list[PersonEntry]:
    """Return all Person rows as PersonEntry objects."""
    result = await session.execute(select(Person).order_by(Person.name))
    return [
        PersonEntry(
            name=row.name,
            role=row.role,
            email=row.email,
            aliases=row.aliases or [],
        )
        for row in result.scalars().all()
    ]


async def load_terms(session: AsyncSession) -> list[TermEntry]:
    """Return all Term rows as TermEntry objects."""
    result = await session.execute(select(Term).order_by(Term.term))
    return [
        TermEntry(
            term=row.term,
            definition=row.definition,
            category=row.category,
        )
        for row in result.scalars().all()
    ]
