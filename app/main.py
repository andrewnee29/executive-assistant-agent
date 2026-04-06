import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from google.oauth2.credentials import Credentials
from sqlalchemy import select

from app.api import auth, chat, meetings
from app.google.meet import list_meetings, match_calendar_title
from app.storage.database import init_db, AsyncSessionLocal
from app.storage.models import UserCredentials
from app.storage.repositories.meetings import save_meeting

logger = logging.getLogger(__name__)

DISCOVER_INTERVAL_SECONDS = 600  # 10 minutes


async def _discovery_loop() -> None:
    while True:
        try:
            await asyncio.sleep(DISCOVER_INTERVAL_SECONDS)
            await _run_discovery()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning("Meeting discovery cycle failed: %s", e)


async def _run_discovery() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserCredentials).where(UserCredentials.user_id == "default")
        )
        row = result.scalar_one_or_none()
        if not row:
            return  # Not authenticated yet — skip silently

        c = row.credentials_json
        credentials = Credentials(
            token=c["token"],
            refresh_token=c.get("refresh_token"),
            token_uri=c.get("token_uri"),
            client_id=c.get("client_id"),
            client_secret=c.get("client_secret"),
            scopes=c.get("scopes"),
        )

    now = datetime.now(timezone.utc)
    found = list_meetings(credentials, now - timedelta(hours=24), now)
    print(f"[discovery] cycle complete: {len(found)} meeting(s) found.", flush=True)
    logger.info("Discovery cycle: %d meeting(s) found.", len(found))

    async with AsyncSessionLocal() as session:
        for m in found:
            m["title"] = match_calendar_title(credentials, m["start_time"], m["end_time"])
            await save_meeting(session, m)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(_discovery_loop())
    try:
        yield
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


app = FastAPI(
    title="Executive Assistant Agent",
    description="Meeting intelligence agent powered by Google Workspace and AI.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(meetings.router, prefix="/meetings", tags=["meetings"])


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}
