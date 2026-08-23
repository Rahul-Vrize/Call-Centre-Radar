"""Primary transcription provider — spends the $49 AssemblyAI free-tier credit
on the commodity step (transcription + speaker labels + word timestamps) so
engineering time goes into the grounded intelligence layer instead.

Deliberately does NOT enable AssemblyAI's built-in Sentiment Analysis / Auto
Chapters / Summarization add-ons: those judgments aren't grounded to a citation
this system controls and verifies, which defeats the point of the pipeline.

Segment/Word timestamps are normalized to seconds (AssemblyAI returns
milliseconds) so both providers speak the same units to the rest of the
pipeline — turns.py's merge logic doesn't need to know which provider ran.
"""
from pathlib import Path

from .base import Transcriber, Segment, Word, Speaker


class AssemblyAIProvider(Transcriber):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("ASSEMBLYAI_API_KEY is not set")
        self.api_key = api_key

        import assemblyai as aai

        aai.settings.api_key = self.api_key
        self._aai = aai
        self._transcriber = aai.Transcriber()

    def transcribe_channel(self, wav_path: Path, speaker: Speaker) -> list[Segment]:
        transcript = self._transcriber.transcribe(str(wav_path))

        if transcript.status == self._aai.TranscriptStatus.error:
            raise RuntimeError(f"AssemblyAI transcription failed for {wav_path}: {transcript.error}")

        segments: list[Segment] = []
        for sentence in transcript.get_sentences():
            words = [
                Word(text=w.text, start=w.start / 1000, end=w.end / 1000, confidence=w.confidence)
                for w in sentence.words
            ]
            segments.append(
                Segment(
                    speaker=speaker,
                    start=sentence.start / 1000,
                    end=sentence.end / 1000,
                    text=sentence.text,
                    words=words,
                )
            )
        return segments
