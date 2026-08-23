"""Merge the two channels' segments into one chronological, turn-by-turn
conversation. Because each channel is single-speaker by construction, this is
ordering + collapsing, not diarization."""
from dataclasses import dataclass, field

from app.pipeline.transcribe.base import Segment, Word, Speaker


@dataclass
class Turn:
    speaker: Speaker
    start: float
    end: float
    text: str
    words: list[Word] = field(default_factory=list)
    overlapping: bool = False


def merge_into_turns(
    agent_segments: list[Segment],
    customer_segments: list[Segment],
    merge_gap_seconds: float = 0.75,
) -> list[Turn]:
    """Sort both channels' segments by start time, collapse consecutive
    same-speaker segments into a single turn (small gaps are just the speaker
    pausing mid-thought, not a new turn), and flag genuine cross-speaker
    time-overlaps (interruptions/crosstalk) instead of forcing a false
    sequential order onto real talk-over.
    """
    all_segments = sorted([*agent_segments, *customer_segments], key=lambda s: s.start)

    turns: list[Turn] = []
    for seg in all_segments:
        prev = turns[-1] if turns else None

        if prev is not None and seg.speaker == prev.speaker and (seg.start - prev.end) <= merge_gap_seconds:
            prev.end = max(prev.end, seg.end)
            prev.text = f"{prev.text} {seg.text}".strip()
            prev.words.extend(seg.words)
            continue

        crosstalk = prev is not None and seg.speaker != prev.speaker and seg.start < prev.end
        if crosstalk:
            prev.overlapping = True

        turns.append(
            Turn(
                speaker=seg.speaker,
                start=seg.start,
                end=seg.end,
                text=seg.text,
                words=list(seg.words),
                overlapping=crosstalk,
            )
        )

    return turns
