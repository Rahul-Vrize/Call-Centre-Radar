"""End-to-end pipeline for one call: split -> transcribe -> merge -> mood ->
shift -> reasoning -> verify -> store. Used both by the overnight batch
(scripts/ingest_dataset.py) and by the live /ingest endpoint — the same code
path either way is what makes the live-demo moment credible."""
from pathlib import Path

from app.config import settings
from app.pipeline.audio import split_channels
from app.pipeline.transcribe import get_transcriber
from app.pipeline.turns import merge_into_turns


def process_call(call_id: str, mp3_path: Path, out_dir: Path) -> None:
    channels = split_channels(mp3_path, out_dir)
    transcriber = get_transcriber(settings.transcriber_provider)

    agent_segments = transcriber.transcribe_channel(channels.agent_wav, "agent")
    customer_segments = transcriber.transcribe_channel(channels.customer_wav, "customer")
    turns = merge_into_turns(agent_segments, customer_segments)

    # TODO: mood scoring per customer turn (mood.py) -> change-point shift (changepoint.py)
    # TODO: LLM reasoning (reasoning.py) -> evidence verification (verifier.py)
    # TODO: attention score (attention_score.py)
    # TODO: persist call + turns + evidence to SQLite (db/session.py)
    raise NotImplementedError
