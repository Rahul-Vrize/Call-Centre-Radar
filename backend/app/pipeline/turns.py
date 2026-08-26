"""Merge the two channels' segments into one chronological, turn-by-turn
conversation. Because each channel is single-speaker by construction, this is
ordering + segmentation, not diarization.
"""
from dataclasses import dataclass, field

from app.pipeline.transcribe.base import Segment, Speaker, Word

#: A silence longer than this within one speaker's audio ends their turn.
#: Also the threshold below which two of their segments are re-joined, so the
#: split and merge steps are exact inverses and nothing round-trips.
DEFAULT_TURN_GAP_SECONDS = 0.8


@dataclass
class Turn:
    speaker: Speaker
    start: float
    end: float
    text: str
    words: list[Word] = field(default_factory=list)
    overlapping: bool = False


def split_on_pauses(
    segments: list[Segment], gap_seconds: float = DEFAULT_TURN_GAP_SECONDS
) -> list[Segment]:
    """Break segments at internal silences.

    Necessary because ASR segment boundaries are not turn boundaries. Each
    channel is transcribed in isolation, so the model never sees the pauses
    where the *other* party was speaking — faster-whisper will happily emit one
    segment spanning a speaker's entire side of the call. Merging that directly
    produces a transcript where the customer says everything at once and the
    agent replies afterwards.

    The pauses we need are already in the word timestamps: a long gap between
    consecutive words on a single-speaker channel is, by construction, where
    the other party was talking. Split there and the conversation interleaves
    correctly. Segments without word timings pass through untouched.
    """
    out: list[Segment] = []

    for seg in segments:
        if len(seg.words) < 2:
            out.append(seg)
            continue

        chunk: list[Word] = [seg.words[0]]
        for prev, word in zip(seg.words, seg.words[1:]):
            if word.start - prev.end > gap_seconds:
                out.append(_segment_from(seg.speaker, chunk))
                chunk = []
            chunk.append(word)

        if chunk:
            out.append(_segment_from(seg.speaker, chunk))

    return out


def _segment_from(speaker: Speaker, words: list[Word]) -> Segment:
    return Segment(
        speaker=speaker,
        start=words[0].start,
        end=words[-1].end,
        text=" ".join(w.text.strip() for w in words).strip(),
        words=list(words),
    )


def merge_into_turns(
    agent_segments: list[Segment],
    customer_segments: list[Segment],
    merge_gap_seconds: float = DEFAULT_TURN_GAP_SECONDS,
) -> list[Turn]:
    """Split both channels on internal pauses, sort by start time, collapse
    consecutive same-speaker segments into a single turn, and flag genuine
    cross-speaker time-overlaps (interruptions, talk-over) rather than forcing
    a false sequential order onto real crosstalk.
    """
    all_segments = sorted(
        [
            *split_on_pauses(agent_segments, merge_gap_seconds),
            *split_on_pauses(customer_segments, merge_gap_seconds),
        ],
        key=lambda s: s.start,
    )

    turns: list[Turn] = []
    for seg in all_segments:
        prev = turns[-1] if turns else None

        if (
            prev is not None
            and seg.speaker == prev.speaker
            and (seg.start - prev.end) <= merge_gap_seconds
        ):
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
