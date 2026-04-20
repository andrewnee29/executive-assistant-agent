from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.database import get_session
from app.storage.models import Term

router = APIRouter()


class TermResponse(BaseModel):
    id: int
    term: str
    definition: str | None
    category: str | None

    class Config:
        from_attributes = True


class TermCreate(BaseModel):
    term: str
    definition: str | None = None
    category: str | None = None


class TermUpdate(BaseModel):
    term: str | None = None
    definition: str | None = None
    category: str | None = None


@router.get("", response_model=list[TermResponse])
async def list_terms(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Term).order_by(Term.term))
    return result.scalars().all()


@router.post("", response_model=TermResponse, status_code=201)
async def create_term(body: TermCreate, session: AsyncSession = Depends(get_session)):
    term = Term(term=body.term, definition=body.definition, category=body.category)
    session.add(term)
    await session.commit()
    await session.refresh(term)
    return term


@router.patch("/{term_id}", response_model=TermResponse)
async def update_term(
    term_id: int, body: TermUpdate, session: AsyncSession = Depends(get_session)
):
    term = await session.get(Term, term_id)
    if not term:
        raise HTTPException(status_code=404, detail="Term not found.")
    if body.term is not None:
        term.term = body.term
    if body.definition is not None:
        term.definition = body.definition
    if body.category is not None:
        term.category = body.category
    await session.commit()
    await session.refresh(term)
    return term


@router.delete("/{term_id}", status_code=204)
async def delete_term(term_id: int, session: AsyncSession = Depends(get_session)):
    term = await session.get(Term, term_id)
    if not term:
        raise HTTPException(status_code=404, detail="Term not found.")
    await session.delete(term)
    await session.commit()
