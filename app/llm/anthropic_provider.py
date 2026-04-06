import json
import re
import anthropic

from app.llm.base import (
    LLMProvider,
    # generate_recap
    RecapInput, RecapOutput,
    # extract_action_items
    ActionItemsInput, ActionItemsOutput, ActionItem,
    # apply_context_corrections
    CorrectionsInput, CorrectionsOutput,
    # analyze_chunk
    ChunkInput, ChunkOutput,
    # propose_kb_updates
    KBUpdateInput, KBUpdateOutput, ProposedPersonUpdate, ProposedTermUpdate,
    PersonEntry, TermEntry,
)

# Model tier assignments
_COMPLEX_MODEL = "claude-opus-4-5"       # generate_recap, analyze_chunk
_SIMPLE_MODEL = "claude-haiku-4-5-20251001"  # extract_action_items, apply_context_corrections, propose_kb_updates


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers before JSON parsing."""
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)


def _format_transcript(entries) -> str:
    return "\n".join(
        f"[{e.timestamp}] {e.speaker}: {e.text}" for e in entries
    )


def _format_people(people) -> str:
    if not people:
        return "None"
    lines = []
    for p in people:
        parts = [p.name]
        if p.role:
            parts.append(p.role)
        if p.email:
            parts.append(p.email)
        if p.aliases:
            parts.append(f"aliases: {', '.join(p.aliases)}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def _format_terms(terms) -> str:
    if not terms:
        return "None"
    lines = []
    for t in terms:
        line = t.term
        if t.definition:
            line += f": {t.definition}"
        if t.category:
            line += f" ({t.category})"
        lines.append(line)
    return "\n".join(lines)


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    # ------------------------------------------------------------------
    # generate_recap
    # ------------------------------------------------------------------

    async def generate_recap(self, input: RecapInput) -> RecapOutput:
        title_line = f"Meeting: {input.meeting_title}\n\n" if input.meeting_title else ""
        transcript_text = _format_transcript(input.transcript)
        people_text = _format_people(input.people)
        terms_text = _format_terms(input.terms)

        system = (
            "You are an executive assistant that writes narrative meeting recaps.\n\n"
            "Rules:\n"
            "- Write flowing prose, not bullet points. Group related ideas into paragraphs.\n"
            "- Use the people list to correct speaker names (aliases are known transcription errors).\n"
            "- Use the terms list to spell project names, acronyms, and tools correctly.\n"
            "- After the narrative, add a section headed 'UNCERTAINTIES:' listing anything you\n"
            "  weren't sure about — ambiguous names, unclear decisions, inaudible segments.\n"
            "  If there are no uncertainties, write 'UNCERTAINTIES: none'."
        )

        user_content = (
            f"{title_line}"
            f"PEOPLE KNOWLEDGE BASE:\n{people_text}\n\n"
            f"TERMS KNOWLEDGE BASE:\n{terms_text}\n\n"
            f"TRANSCRIPT:\n{transcript_text}"
        )

        try:
            response = await self._client.messages.create(
                model=_COMPLEX_MODEL,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user_content}],
            )
        except anthropic.APIError as e:
            raise RuntimeError(f"generate_recap API call failed: {e}") from e

        raw = response.content[0].text

        # Split narrative from uncertainties block
        if "UNCERTAINTIES:" in raw:
            narrative_part, uncertainty_part = raw.split("UNCERTAINTIES:", 1)
            summary = narrative_part.strip()
            uncertainty_lines = uncertainty_part.strip().splitlines()
            uncertainties = [
                line.lstrip("-• ").strip()
                for line in uncertainty_lines
                if line.strip() and line.strip().lower() != "none"
            ]
        else:
            summary = raw.strip()
            uncertainties = []

        return RecapOutput(summary=summary, uncertainties=uncertainties)

    # ------------------------------------------------------------------
    # extract_action_items
    # ------------------------------------------------------------------

    async def extract_action_items(self, input: ActionItemsInput) -> ActionItemsOutput:
        transcript_text = _format_transcript(input.transcript)

        system = (
            f"You extract action items for {input.user_name} ONLY from meeting transcripts.\n\n"
            "Rules:\n"
            f"- Only include tasks where {input.user_name} is the one who needs to do something.\n"
            "- Do NOT extract tasks assigned to other people.\n"
            "- Every item must have a timestamp citation in [HH:MM:SS] format from the transcript.\n"
            "- The context field should be a brief verbatim quote or close paraphrase.\n\n"
            "Respond with a JSON array and nothing else. Schema:\n"
            '[\n'
            '  {\n'
            '    "task": "description of what needs to be done",\n'
            '    "timestamp": "HH:MM:SS",\n'
            '    "context": "quote or paraphrase from transcript"\n'
            '  }\n'
            ']'
        )

        user_content = (
            f"MEETING SUMMARY (for context):\n{input.summary}\n\n"
            f"TRANSCRIPT:\n{transcript_text}"
        )

        try:
            response = await self._client.messages.create(
                model=_SIMPLE_MODEL,
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": user_content}],
            )
        except anthropic.APIError as e:
            raise RuntimeError(f"extract_action_items API call failed: {e}") from e

        raw = _strip_code_fences(response.content[0].text)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"extract_action_items: model returned invalid JSON — {e}\nRaw: {raw}"
            ) from e

        items = [
            ActionItem(
                task=item["task"],
                timestamp=item["timestamp"],
                context=item["context"],
            )
            for item in data
        ]
        return ActionItemsOutput(items=items)

    # ------------------------------------------------------------------
    # apply_context_corrections
    # ------------------------------------------------------------------

    async def apply_context_corrections(self, input: CorrectionsInput) -> CorrectionsOutput:
        corrections_list = "\n".join(
            f'  "{wrong}" → "{right}"' for wrong, right in input.corrections.items()
        )

        system = (
            "You apply a corrections map to text. Replace every occurrence of each wrong token\n"
            "with the correct one. Preserve surrounding punctuation and capitalisation style.\n\n"
            "After the corrected text, on a new line write 'APPLIED:' followed by a comma-separated\n"
            "list of the wrong tokens you actually replaced. If none were found, write 'APPLIED: none'."
        )

        user_content = (
            f"CORRECTIONS MAP:\n{corrections_list}\n\n"
            f"TEXT:\n{input.text}"
        )

        try:
            response = await self._client.messages.create(
                model=_SIMPLE_MODEL,
                max_tokens=len(input.text.split()) * 2 + 256,
                system=system,
                messages=[{"role": "user", "content": user_content}],
            )
        except anthropic.APIError as e:
            raise RuntimeError(f"apply_context_corrections API call failed: {e}") from e

        raw = response.content[0].text

        if "APPLIED:" in raw:
            text_part, applied_part = raw.split("APPLIED:", 1)
            corrected_text = text_part.strip()
            applied_raw = applied_part.strip()
            if applied_raw.lower() == "none":
                applied = []
            else:
                applied = [t.strip().strip('"') for t in applied_raw.split(",") if t.strip()]
        else:
            corrected_text = raw.strip()
            applied = []

        return CorrectionsOutput(corrected_text=corrected_text, applied=applied)

    # ------------------------------------------------------------------
    # analyze_chunk
    # ------------------------------------------------------------------

    async def analyze_chunk(self, input: ChunkInput) -> ChunkOutput:
        chunk_label = f"chunk {input.chunk_index + 1} of {input.total_chunks}"
        transcript_text = _format_transcript(input.entries)

        prior_context = ""
        if input.prior_summaries:
            numbered = "\n\n".join(
                f"Chunk {i + 1} summary:\n{s}"
                for i, s in enumerate(input.prior_summaries)
            )
            prior_context = f"PRIOR CHUNK SUMMARIES (for continuity):\n{numbered}\n\n"

        system = (
            f"You are summarising {chunk_label} of a multi-part meeting transcript.\n\n"
            "Rules:\n"
            "- Write a concise narrative summary of this segment in flowing prose.\n"
            "- Use the prior chunk summaries to maintain continuity — reference ongoing threads.\n"
            "- At the end, under the heading 'ACTION ITEM CANDIDATES:', list any tasks you spotted\n"
            "  for the user. Each must have a [HH:MM:SS] timestamp and a brief context quote.\n"
            "  Format each candidate as: [HH:MM:SS] | task description | context quote\n"
            "  If none found, write 'ACTION ITEM CANDIDATES: none'."
        )

        user_content = f"{prior_context}TRANSCRIPT SEGMENT:\n{transcript_text}"

        try:
            response = await self._client.messages.create(
                model=_COMPLEX_MODEL,
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": user_content}],
            )
        except anthropic.APIError as e:
            raise RuntimeError(f"analyze_chunk API call failed (chunk {input.chunk_index}): {e}") from e

        raw = response.content[0].text
        candidates: list[ActionItem] = []

        if "ACTION ITEM CANDIDATES:" in raw:
            summary_part, candidates_part = raw.split("ACTION ITEM CANDIDATES:", 1)
            summary = summary_part.strip()
            for line in candidates_part.strip().splitlines():
                line = line.strip()
                if not line or line.lower() == "none":
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) == 3:
                    candidates.append(ActionItem(
                        timestamp=parts[0].strip("[]"),
                        task=parts[1],
                        context=parts[2],
                    ))
        else:
            summary = raw.strip()

        return ChunkOutput(summary=summary, action_item_candidates=candidates)

    # ------------------------------------------------------------------
    # propose_kb_updates
    # ------------------------------------------------------------------

    async def propose_kb_updates(self, input: KBUpdateInput) -> KBUpdateOutput:
        new_people_text = _format_people(input.new_people) if input.new_people else "None"
        new_terms_text = _format_terms(input.new_terms) if input.new_terms else "None"
        existing_people_text = _format_people(input.existing_people) if input.existing_people else "None"
        existing_terms_text = _format_terms(input.existing_terms) if input.existing_terms else "None"

        system = (
            "You manage a knowledge base for a meeting intelligence system.\n\n"
            "Review the new people and terms discovered in this session and propose\n"
            "what should be added or updated in the knowledge base.\n\n"
            "For each proposal include:\n"
            '- "action": "add" (new entry) or "update" (modify existing)\n'
            '- "rationale": one sentence explaining why\n\n'
            "Respond with a JSON object and nothing else. Schema:\n"
            "{\n"
            '  "people": [\n'
            '    {\n'
            '      "name": "...",\n'
            '      "role": "...",\n'
            '      "email": "...",\n'
            '      "aliases": [...],\n'
            '      "action": "add" | "update",\n'
            '      "rationale": "..."\n'
            '    }\n'
            "  ],\n"
            '  "terms": [\n'
            '    {\n'
            '      "term": "...",\n'
            '      "definition": "...",\n'
            '      "category": "project" | "acronym" | "tool" | "other",\n'
            '      "action": "add" | "update",\n'
            '      "rationale": "..."\n'
            '    }\n'
            "  ]\n"
            "}"
        )

        user_content = (
            f"EXISTING PEOPLE KB:\n{existing_people_text}\n\n"
            f"EXISTING TERMS KB:\n{existing_terms_text}\n\n"
            f"NEW PEOPLE FROM THIS SESSION:\n{new_people_text}\n\n"
            f"NEW TERMS FROM THIS SESSION:\n{new_terms_text}"
        )

        try:
            response = await self._client.messages.create(
                model=_SIMPLE_MODEL,
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": user_content}],
            )
        except anthropic.APIError as e:
            raise RuntimeError(f"propose_kb_updates API call failed: {e}") from e

        raw = _strip_code_fences(response.content[0].text)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"propose_kb_updates: model returned invalid JSON — {e}\nRaw: {raw}"
            ) from e

        proposed_people = [
            ProposedPersonUpdate(
                person=PersonEntry(
                    name=p["name"],
                    role=p.get("role"),
                    email=p.get("email"),
                    aliases=p.get("aliases", []),
                ),
                action=p.get("action", "add"),
                rationale=p.get("rationale", ""),
            )
            for p in data.get("people", [])
        ]

        proposed_terms = [
            ProposedTermUpdate(
                term=TermEntry(
                    term=t["term"],
                    definition=t.get("definition"),
                    category=t.get("category"),
                ),
                action=t.get("action", "add"),
                rationale=t.get("rationale", ""),
            )
            for t in data.get("terms", [])
        ]

        return KBUpdateOutput(proposed_people=proposed_people, proposed_terms=proposed_terms)
