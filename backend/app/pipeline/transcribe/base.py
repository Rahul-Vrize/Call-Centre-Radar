"""The provider interface.

Swapping providers is a config change (TRANSCRIBER_PROVIDER in .env), never a
rewrite of the rest of the pipeline.

The interface is built around `transcribe_call(stereo_path)` rather than
per-channel calls, because the best providers handle the stereo file natively:
AssemblyAI's multichannel mode returns channel-tagged words from ONE request,
halving round trips and removing the channel-split step from the ASR path
entirely. Providers that can only see one speaker at a time (faster-whisper)
implement `transcribe_call` by splitting and calling themselves twice — the
cost lands on the provider that needs it, not on every caller.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Speaker = Literal["agent", "customer"]

# The dataset's channel convention, stated once. Left is the agent, right is
# the customer — this is the whole diarization step.
CHANNEL_SPEAKERS: dict[int, Speaker] = {1: "agent", 2: "customer"}


@dataclass
class Word:
    text: str
    start: float  # seconds
    end: float
    confidence: float


@dataclass
class Segment:
    speaker: Speaker
    start: float
    end: float
    text: str
    words: list[Word] = field(default_factory=list)


class Transcriber(ABC):
    """Transcribes a call into speaker-attributed, timestamped segments.

    Implementations must return word-level timestamps — the evidence verifier
    and the mood-shift citation both depend on pointing at an exact moment in
    the audio, not just "somewhere in this segment".
    """

    #: Identifies cached transcripts on disk, so switching providers never
    #: serves you the other one's output.
    name: str = "base"

    @abstractmethod
    def transcribe_call(self, stereo_path: Path, work_dir: Path) -> list[Segment]:
        """Transcribe a full stereo call into merged, speaker-tagged segments.

        `work_dir` is scratch space for providers that need to split channels;
        callers are responsible for cleaning it up.
        """
        ...
