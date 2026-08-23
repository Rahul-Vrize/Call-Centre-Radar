"""Offline fallback provider — faster-whisper (CTranslate2). Zero API key, zero
network dependency: this is what keeps the README's "runs from scratch" claim
true regardless of AssemblyAI credit balance, and the safety net if the live
demo's /ingest call needs to work without network access.
"""
from pathlib import Path

from .base import Transcriber, Segment, Word, Speaker


class WhisperProvider(Transcriber):
    def __init__(self, model_size: str, device: str, compute_type: str):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None  # lazy-loaded — avoid paying model load cost at import time

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size, device=self.device, compute_type=self.compute_type
            )
        return self._model

    def transcribe_channel(self, wav_path: Path, speaker: Speaker) -> list[Segment]:
        model = self._load()
        segments, _info = model.transcribe(str(wav_path), word_timestamps=True, vad_filter=True)
        result: list[Segment] = []
        for seg in segments:
            words = [
                Word(text=w.word, start=w.start, end=w.end, confidence=w.probability)
                for w in (seg.words or [])
            ]
            result.append(Segment(speaker=speaker, start=seg.start, end=seg.end, text=seg.text, words=words))
        return result
