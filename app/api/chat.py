from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.agent import AgentOrchestrator

router = APIRouter()


class ChatMessage(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str


@router.post("/message", response_model=ChatResponse)
async def send_message(
    body: ChatMessage,
    agent: AgentOrchestrator = Depends(AgentOrchestrator),
):
    """Send a message to the agent and receive a reply."""
    reply, conversation_id = await agent.handle_message(
        body.message, body.conversation_id
    )
    return ChatResponse(reply=reply, conversation_id=conversation_id)


@router.get("/history/{conversation_id}")
async def get_history(conversation_id: str):
    """Retrieve conversation history."""
    # TODO: fetch from storage
    return {"conversation_id": conversation_id, "messages": []}
