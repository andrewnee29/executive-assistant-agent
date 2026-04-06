import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.storage.models import Base


def _async_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "sqlite:///./data/app.db")
    # Heroku sets postgres://, SQLAlchemy needs postgresql+asyncpg://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    # Local SQLite
    if url.startswith("sqlite:///"):
        url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


_engine = create_async_engine(
    _async_database_url(),
    echo=os.environ.get("DEBUG", "false").lower() == "true",
)

AsyncSessionLocal = sessionmaker(
    _engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db() -> None:
    """Create all tables. Called once at startup."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
