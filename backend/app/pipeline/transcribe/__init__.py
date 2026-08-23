from .base import Transcriber, Segment, Word
from .assemblyai_provider import AssemblyAIProvider
from .whisper_provider import WhisperProvider


def get_transcriber(provider: str) -> Transcriber:
    if provider == "assemblyai":
        from app.config import settings
        return AssemblyAIProvider(api_key=settings.assemblyai_api_key)
    if provider == "whisper":
        from app.config import settings
        return WhisperProvider(
            model_size=settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    raise ValueError(f"unknown transcriber provider: {provider!r}")


__all__ = ["Transcriber", "Segment", "Word", "AssemblyAIProvider", "WhisperProvider", "get_transcriber"]
