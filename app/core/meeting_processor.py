from dataclasses import dataclass, field
from typing import Callable, Awaitable

from app.llm.base import (
    LLMProvider,
    TranscriptEntry, PersonEntry, TermEntry,
    RecapInput, ActionItemsInput, ChunkInput, ActionItem,
)
from app.llm.factory import get_llm_provider

CHUNK_THRESHOLD = 500
NUM_CHUNKS = 4

ProgressCallback = Callable[[dict], Awaitable[None]]


async def _noop_progress(state: dict) -> None:
    pass


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
    on_progress: ProgressCallback | None = None,
) -> ProcessedMeeting:
    if llm is None:
        llm = get_llm_provider()
    if on_progress is None:
        on_progress = _noop_progress

    people = people or []
    terms = terms or []

    if len(transcript) < CHUNK_THRESHOLD:
        return await _single_pass(transcript, meeting_title, people, terms, user_name, llm, on_progress)
    else:
        return await _chunked(transcript, meeting_title, people, terms, user_name, llm, on_progress)


async def _single_pass(
    transcript: list[TranscriptEntry],
    meeting_title: str | None,
    people: list[PersonEntry],
    terms: list[TermEntry],
    user_name: str,
    llm: LLMProvider,
    on_progress: ProgressCallback,
) -> ProcessedMeeting:
    await on_progress({"step": 3, "total_steps": 4, "label": "Analyzing transcript with AI..."})
    recap = await llm.generate_recap(
        RecapInput(transcript=transcript, people=people, terms=terms, meeting_title=meeting_title)
    )
    await on_progress({"step": 4, "total_steps": 4, "label": "Extracting action items..."})
    action_items_result = await llm.extract_action_items(
        ActionItemsInput(transcript=transcript, summary=recap.summary, user_name=user_name)
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
    on_progress: ProgressCallback,
) -> ProcessedMeeting:
    chunk_size = len(transcript) // NUM_CHUNKS
    chunks = [transcript[i * chunk_size: (i + 1) * chunk_size] for i in range(NUM_CHUNKS)]
    chunks[-1] += transcript[NUM_CHUNKS * chunk_size:]

    prior_summaries: list[str] = []
    all_candidates: list[ActionItem] = []

    for i, chunk in enumerate(chunks):
        chunk_states = [
            {"index": j, "status": "done" if j < i else "active" if j == i else "pending"}
            for j in range(NUM_CHUNKS)
        ]
        await on_progress({
            "step": 3, "total_steps": 4,
            "label": "Analyzing transcript with AI...",
            "chunks": chunk_states,
        })
        result = await llm.analyze_chunk(
            ChunkInput(entries=chunk, chunk_index=i, total_chunks=NUM_CHUNKS, prior_summaries=prior_summaries)
        )
        prior_summaries.append(result.summary)
        all_candidates.extend(result.action_item_candidates)

    await on_progress({"step": 4, "total_steps": 4, "label": "Extracting action items..."})
    combined_summary = "\n\n".join(prior_summaries)
    action_items_result = await llm.extract_action_items(
        ActionItemsInput(transcript=transcript, summary=combined_summary, user_name=user_name)
    )
    return ProcessedMeeting(
        summary=combined_summary,
        action_items=action_items_result.items,
        uncertainties=[],
    )
