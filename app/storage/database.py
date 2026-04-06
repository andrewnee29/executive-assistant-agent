from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.config import get_settings
from app.storage.models import Base

settings = get_settings()

# SQLite for local dev; swap DATABASE_URL in .env for Postgres in production
_engine = create_async_engine(
    settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///"),
    echo=settings.debug,
)

AsyncSessionLocal = sessionmaker(
    _engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db():
    """Create all tables. Call once at startup."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
