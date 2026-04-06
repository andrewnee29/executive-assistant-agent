from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import auth, chat, meetings, actions

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Meeting intelligence agent powered by Google Workspace and AI.",
    version="0.1.0",
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
app.include_router(actions.router, prefix="/actions", tags=["actions"])


@app.get("/health")
async def health():
    return {"status": "ok"}
