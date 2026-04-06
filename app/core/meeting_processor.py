from app.llm.base import LLMProvider, Message
from app.storage.models import Meeting, Transcript


CHUNK_THRESHOLD = 500  # entries — meetings larger than this get chunked


class MeetingProcessor:
    """Generates recaps and extracts action items from transcripts."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def generate_recap(
        self, meeting: Meeting, transcript: Transcript, context: dict
    ) -> str:
        """Generate a narrative recap. Uses chunked processing for long meetings."""
        entries = transcript.entries
        if len(entries) > CHUNK_THRESHOLD:
            return await self._chunked_recap(meeting, entries, context)
        return await self._single_pass_recap(meeting, entries, context)

    async def extract_action_items(
        self, meeting: Meeting, transcript: Transcript
    ) -> list[dict]:
        """Extract action items for the user only (not other attendees)."""
        # TODO: implement extraction with timestamp citations
        return []

    async def _single_pass_recap(
        self, meeting: Meeting, entries: list, context: dict
    ) -> str:
        transcript_text = self._format_entries(entries)
        response = await self.llm.complete(
            messages=[Message(role="user", content=transcript_text)],
            system=self._recap_system_prompt(meeting, context),
        )
        return response.content

    async def _chunked_recap(
        self, meeting: Meeting, entries: list, context: dict
    ) -> str:
        # Split into time-based segments, process in parallel, then consolidate
        # TODO: implement parallel chunk processing with progress streaming
        chunk_size = len(entries) // 4
        chunks = [entries[i : i + chunk_size] for i in range(0, len(entries), chunk_size)]

        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            text = self._format_entries(chunk)
            response = await self.llm.complete(
                messages=[Message(role="user", content=text)],
                system=f"Summarize segment {i + 1} of {len(chunks)} from this meeting.",
            )
            chunk_summaries.append(response.content)

        combined = "\n\n---\n\n".join(chunk_summaries)
        consolidation = await self.llm.complete(
            messages=[Message(role="user", content=combined)],
            system=self._recap_system_prompt(meeting, context),
        )
        return consolidation.content

    def _format_entries(self, entries: list) -> str:
        return "\n".join(
            f"[{e.get('timestamp', '')}] {e.get('speaker', 'Unknown')}: {e.get('text', '')}"
            for e in entries
        )

    def _recap_system_prompt(self, meeting: Meeting, context: dict) -> str:
        people = context.get("people", "")
        terms = context.get("terms", "")
        return (
            f"Generate a narrative meeting recap for '{meeting.title}'.\n"
            f"Known people: {people}\n"
            f"Known terms: {terms}\n"
            "Focus on decisions made, key discussion points, and narrative flow — "
            "not just bullet points. Apply context corrections for known transcription errors."
        )
