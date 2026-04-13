from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.database import get_session
from app.storage.models import Person

router = APIRouter()


class PersonResponse(BaseModel):
    id: int
    name: str
    role: str | None
    team: str | None
    email: str | None
    aliases: list[str]
    notes: str | None

    class Config:
        from_attributes = True


class PersonCreate(BaseModel):
    name: str
    role: str | None = None
    team: str | None = None
    email: str | None = None
    aliases: list[str] = []
    notes: str | None = None


class PersonUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    team: str | None = None
    email: str | None = None
    aliases: list[str] | None = None
    notes: str | None = None


@router.get("", response_model=list[PersonResponse])
async def list_people(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Person).order_by(Person.name))
    return result.scalars().all()


@router.post("", response_model=PersonResponse, status_code=201)
async def create_person(body: PersonCreate, session: AsyncSession = Depends(get_session)):
    person = Person(name=body.name, role=body.role, team=body.team, email=body.email, aliases=body.aliases, notes=body.notes)
    session.add(person)
    await session.commit()
    await session.refresh(person)
    return person


@router.patch("/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: int, body: PersonUpdate, session: AsyncSession = Depends(get_session)
):
    person = await session.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found.")
    if body.name is not None:
        person.name = body.name
    if body.role is not None:
        person.role = body.role
    if body.email is not None:
        person.email = body.email
    if body.aliases is not None:
        person.aliases = body.aliases
    if body.team is not None:
        person.team = body.team
    if body.notes is not None:
        person.notes = body.notes
    await session.commit()
    await session.refresh(person)
    return person


@router.delete("/{person_id}", status_code=204)
async def delete_person(person_id: int, session: AsyncSession = Depends(get_session)):
    person = await session.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found.")
    await session.delete(person)
    await session.commit()
