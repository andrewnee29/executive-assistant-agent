from app.llm.base import LLMProvider, Message


class ContextManager:
    """Manages the agent's growing knowledge base of people and terms.

    The AI — not the user — proposes updates. Nothing is saved without user approval.
    """

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def propose_people_updates(
        self, transcript_participants: list[dict], known_people: list[dict]
    ) -> list[dict]:
        """Identify new people and suggested corrections from a transcript."""
        # TODO: cross-reference with Google Directory for auto-population
        new_people = []
        known_names = {p["name"].lower() for p in known_people}
        for participant in transcript_participants:
            if participant["name"].lower() not in known_names:
                new_people.append({
                    "name": participant["name"],
                    "source": "transcript",
                    "suggested_role": None,
                })
        return new_people

    async def propose_term_updates(
        self, transcript_text: str, known_terms: list[dict]
    ) -> list[dict]:
        """Identify new project names, acronyms, or vocabulary from a transcript."""
        known = [t["term"] for t in known_terms]
        response = await self.llm.complete(
            messages=[
                Message(
                    role="user",
                    content=(
                        f"Known terms: {', '.join(known)}\n\n"
                        f"Transcript excerpt:\n{transcript_text[:3000]}"
                    ),
                )
            ],
            system=(
                "Identify any new project names, acronyms, or organizational vocabulary "
                "in the transcript that are NOT in the known terms list. "
                "Return as a JSON array of {term, context} objects."
            ),
        )
        # TODO: parse JSON from response.content
        return []

    async def detect_transcription_corrections(
        self, transcript_text: str, known_people: list[dict]
    ) -> list[dict]:
        """Detect likely transcription errors (e.g., 'Phoebe' → 'Amy Fieber')."""
        # TODO: implement pattern matching + LLM-assisted correction proposals
        return []
