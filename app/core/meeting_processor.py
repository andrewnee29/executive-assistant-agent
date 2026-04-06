from dataclasses import dataclass, field

from app.llm.base import (
    LLMProvider,
    TranscriptEntry, PersonEntry, TermEntry,
    RecapInput, ActionItemsInput, ChunkInput, ActionItem,
)
from app.llm.factory import get_llm_provider

CHUNK_THRESHOLD = 500
NUM_CHUNKS = 4


@dataclass
class ProcessedMeeting:
    summary: str
    action_items: list[ActionItem] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)


async def process_meeting(
    transcript: list[TranscriptEntry],
    meeting_title: str | None = None,
    people: list[PersonEntry] | None = None,
    terms: list[TermEntry] | None = None,
    user_name: str = "the user",
    llm: LLMProvider | None = None,
) -> ProcessedMeeting:
    """Process a transcript into a recap and action items.

    Uses single-pass for short meetings (<500 entries) and chunked
    sequential processing for long ones (>=500 entries).
    """
    if llm is None:
        llm = get_llm_provider()

    people = people or []
    terms = terms or []

    if len(transcript) < CHUNK_THRESHOLD:
        return await _single_pass(transcript, meeting_title, people, terms, user_name, llm)
    else:
        return await _chunked(transcript, meeting_title, people, terms, user_name, llm)


async def _single_pass(
    transcript: list[TranscriptEntry],
    meeting_title: str | None,
    people: list[PersonEntry],
    terms: list[TermEntry],
    user_name: str,
    llm: LLMProvider,
) -> ProcessedMeeting:
    recap = await llm.generate_recap(
        RecapInput(
            transcript=transcript,
            people=people,
            terms=terms,
            meeting_title=meeting_title,
        )
    )
    action_items_result = await llm.extract_action_items(
        ActionItemsInput(
            transcript=transcript,
            summary=recap.summary,
            user_name=user_name,
        )
    )
    return ProcessedMeeting(
        summary=recap.summary,
        action_items=action_items_result.items,
        uncertainties=recap.uncertainties,
    )


async def _chunked(
    transcript: list[TranscriptEntry],
    meeting_title: str | None,
    people: list[PersonEntry],
    terms: list[TermEntry],
    user_name: str,
    llm: LLMProvider,
) -> ProcessedMeeting:
    chunk_size = len(transcript) // NUM_CHUNKS
    chunks = [
        transcript[i * chunk_size: (i + 1) * chunk_size]
        for i in range(NUM_CHUNKS)
    ]
    # Any remainder goes into the last chunk
    chunks[-1] += transcript[NUM_CHUNKS * chunk_size:]

    prior_summaries: list[str] = []
    all_candidates: list[ActionItem] = []

    for i, chunk in enumerate(chunks):
        result = await llm.analyze_chunk(
            ChunkInput(
                entries=chunk,
                chunk_index=i,
                total_chunks=NUM_CHUNKS,
                prior_summaries=prior_summaries,
            )
        )
        prior_summaries.append(result.summary)
        all_candidates.extend(result.action_item_candidates)

    combined_summary = "\n\n".join(prior_summaries)

    # Confirm candidates against the full combined summary
    action_items_result = await llm.extract_action_items(
        ActionItemsInput(
            transcript=transcript,
            summary=combined_summary,
            user_name=user_name,
        )
    )

    return ProcessedMeeting(
        summary=combined_summary,
        action_items=action_items_result.items,
        uncertainties=[],
    )
