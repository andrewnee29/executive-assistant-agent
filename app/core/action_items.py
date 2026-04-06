from app.llm.base import LLMProvider, Message


class ActionItemExtractor:
    """Extracts action items for the user only, with transcript timestamp citations."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def extract(
        self,
        transcript_entries: list[dict],
        user_name: str,
    ) -> list[dict]:
        """
        Returns a list of action items, each with:
          - task: str
          - timestamp: str (transcript timestamp)
          - context: str (surrounding quote for reference)
        """
        transcript_text = self._format_entries(transcript_entries)
        response = await self.llm.complete(
            messages=[Message(role="user", content=transcript_text)],
            system=(
                f"Extract action items ONLY for {user_name} from this meeting transcript. "
                "Do NOT extract tasks for other participants. "
                "For each item include: task description, the timestamp it was mentioned, "
                "and a brief quote from the transcript for context. "
                "Return as a JSON array of {{task, timestamp, context}} objects."
            ),
        )
        # TODO: parse and validate JSON from response.content
        return []

    async def deduplicate(
        self, items: list[dict], existing_open_items: list[dict]
    ) -> list[dict]:
        """Remove action items already tracked from previous meetings."""
        # TODO: semantic similarity check against existing open items
        return items

    def _format_entries(self, entries: list[dict]) -> str:
        return "\n".join(
            f"[{e.get('timestamp', '')}] {e.get('speaker', '')}: {e.get('text', '')}"
            for e in entries
        )
