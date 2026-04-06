from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Shared vocabulary types
# ---------------------------------------------------------------------------

@dataclass
class TranscriptEntry:
    timestamp: str
    speaker: str
    text: str


@dataclass
class PersonEntry:
    name: str
    role: str | None = None
    email: str | None = None
    aliases: list[str] = field(default_factory=list)  # known transcription mis-spellings


@dataclass
class TermEntry:
    term: str
    definition: str | None = None
    category: str | None = None  # "project" | "acronym" | "tool" | "other"


# ---------------------------------------------------------------------------
# generate_recap
# ---------------------------------------------------------------------------

@dataclass
class RecapInput:
    transcript: list[TranscriptEntry]
    people: list[PersonEntry]
    terms: list[TermEntry]
    meeting_title: str | None = None


@dataclass
class RecapOutput:
    summary: str
    # Things the model wasn't sure about — surface to user for validation
    uncertainties: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# extract_action_items
# ---------------------------------------------------------------------------

@dataclass
class ActionItemsInput:
    transcript: list[TranscriptEntry]
    summary: str
    # Only extract tasks for this person
    user_name: str


@dataclass
class ActionItem:
    task: str
    timestamp: str        # e.g. "00:14:32" — points back into the transcript
    context: str          # verbatim quote or paraphrase for reference


@dataclass
class ActionItemsOutput:
    items: list[ActionItem]


# ---------------------------------------------------------------------------
# apply_context_corrections
# ---------------------------------------------------------------------------

@dataclass
class CorrectionsInput:
    text: str
    # Maps a wrong token → correct token, e.g. {"Phoebe": "Amy Fieber"}
    corrections: dict[str, str]


@dataclass
class CorrectionsOutput:
    corrected_text: str
    # Corrections that were actually applied (may be a subset of the map)
    applied: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# analyze_chunk
# ---------------------------------------------------------------------------

@dataclass
class ChunkInput:
    entries: list[TranscriptEntry]
    chunk_index: int        # 0-based
    total_chunks: int
    # Summaries of chunks already processed, for continuity
    prior_summaries: list[str] = field(default_factory=list)


@dataclass
class ChunkOutput:
    summary: str
    # Action item candidates spotted in this chunk (de-duplicated later)
    action_item_candidates: list[ActionItem] = field(default_factory=list)


# ---------------------------------------------------------------------------
# propose_kb_updates
# ---------------------------------------------------------------------------

@dataclass
class KBUpdateInput:
    # New people encountered in this session (not yet in the knowledge base)
    new_people: list[PersonEntry]
    # New terms encountered in this session
    new_terms: list[TermEntry]
    # Existing KB for context — model can suggest corrections to existing entries too
    existing_people: list[PersonEntry] = field(default_factory=list)
    existing_terms: list[TermEntry] = field(default_factory=list)


@dataclass
class ProposedPersonUpdate:
    person: PersonEntry
    # "add" = new entry, "update" = modify an existing entry
    action: str
    rationale: str


@dataclass
class ProposedTermUpdate:
    term: TermEntry
    action: str
    rationale: str


@dataclass
class KBUpdateOutput:
    proposed_people: list[ProposedPersonUpdate] = field(default_factory=list)
    proposed_terms: list[ProposedTermUpdate] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Abstract provider interface
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    """Abstract interface for all LLM providers.

    Swap providers by changing LLM_PROVIDER in .env — no other code changes needed.
    Concrete implementations live in anthropic_provider.py and openai_provider.py.
    """

    @abstractmethod
    async def generate_recap(self, input: RecapInput) -> RecapOutput:
        """Generate a narrative summary of a meeting transcript.

        Uses the people and terms knowledge bases to resolve names and vocabulary,
        and flags anything the model is uncertain about for user validation.
        """
        ...

    @abstractmethod
    async def extract_action_items(self, input: ActionItemsInput) -> ActionItemsOutput:
        """Extract tasks for the user only, each anchored to a transcript timestamp."""
        ...

    @abstractmethod
    async def apply_context_corrections(self, input: CorrectionsInput) -> CorrectionsOutput:
        """Apply a corrections map to raw text (e.g. fix transcription errors)."""
        ...

    @abstractmethod
    async def analyze_chunk(self, input: ChunkInput) -> ChunkOutput:
        """Summarize one segment of a long transcript, aware of preceding chunks.

        Used by the chunked processing path for meetings with 500+ entries.
        """
        ...

    @abstractmethod
    async def propose_kb_updates(self, input: KBUpdateInput) -> KBUpdateOutput:
        """Propose additions or corrections to the people and terms knowledge bases.

        The agent calls this at the end of a processing session. Nothing is
        persisted until the user approves the proposals.
        """
        ...
