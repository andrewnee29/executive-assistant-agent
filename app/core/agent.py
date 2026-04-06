import uuid
from fastapi import Depends

from app.config import Settings, get_settings
from app.llm.base import LLMProvider, Message
from app.llm.factory import get_llm_provider


class AgentOrchestrator:
    """Routes user messages to the appropriate workflow and returns replies."""

    def __init__(self, settings: Settings = Depends(get_settings)):
        self.llm: LLMProvider = get_llm_provider(settings)

    async def handle_message(
        self, user_message: str, conversation_id: str | None = None
    ) -> tuple[str, str]:
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        # TODO: load conversation history from storage
        history: list[Message] = []
        history.append(Message(role="user", content=user_message))

        response = await self.llm.complete(
            messages=history,
            system=self._system_prompt(),
        )

        # TODO: persist assistant message to storage
        return response.content, conversation_id

    def _system_prompt(self) -> str:
        # TODO: load from reference/system-prompt.md and inject dynamic context
        return (
            "You are an executive assistant agent. You help the user process "
            "meeting transcripts, generate recaps, extract action items, and "
            "manage their professional context."
        )
