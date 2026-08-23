"""The provider interface. Swapping AssemblyAI <-> faster-whisper is a config
change (TRANSCRIBER_PROVIDER in .env), never a rewrite of the rest of the
pipeline — see the "Provider strategy" section of RADAR_PLAYBOOK.md."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Speaker = Literal["agent", "customer"]


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
    """Transcribes a single mono channel of a call into timestamped segments.

    Implementations must return word-level timestamps — the evidence verifier
    and the mood-shift citation both depend on being able to point at an exact
    moment in the audio, not just "somewhere in this segment."
    """

    @abstractmethod
    def transcribe_channel(self, wav_path: Path, speaker: Speaker) -> list[Segment]:
        ...
