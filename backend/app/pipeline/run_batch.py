"""End-to-end pipeline for one call.

Used by both the overnight batch (scripts/ingest_dataset.py) and the live
/ingest endpoint. The same code path either way is what makes the live-demo
moment credible rather than a separate happy path built for the stage.

Stage 1 (this file, today): split -> transcribe -> merge -> store.
Stages 2-5 (mood, reasoning, verification, attention) hang off `analyze_call`
and are added next; a call can sit transcribed-but-unanalyzed without breaking
anything that reads it.
"""
import shutil
import sqlite3
from pathlib import Path

from app.config import settings
from app.db import store
from app.pipeline import cache
from app.pipeline.metadata import CallMetadata
from app.pipeline.transcribe import Transcriber, get_transcriber
from app.pipeline.turns import Turn, merge_into_turns


def transcribe_call(
    meta: CallMetadata,
    audio_path: Path,
    cache_dir: Path,
    work_dir: Path,
    transcriber: Transcriber,
    force: bool = False,
) -> list[Turn]:
    """Transcribe one call into merged turns. Touches no database.

    Deliberately DB-free so it can run on a worker thread. Transcription is
    network-bound (AssemblyAI) or CPU-bound (whisper) and is by far the slowest
    step; keeping SQLite out of it means the caller can fan this out across a
    pool and still do all writes from one thread, avoiding SQLite's threading
    constraints entirely.
    """
    provider = transcriber.name
    segments = None if force else cache.load(cache_dir, meta.call_id, provider)

    if segments is None:
        call_work = work_dir / meta.call_id
        call_work.mkdir(parents=True, exist_ok=True)
        try:
            segments = transcriber.transcribe_call(audio_path, call_work)
            # Cache before anything downstream runs. If turn-merging or storage
            # throws, the expensive step is already banked.
            cache.store(cache_dir, meta.call_id, provider, segments)
        finally:
            # 16kHz mono wavs are ~11x the mp3 size; across 1,441 calls that is
            # ~5.4GB of intermediates nothing ever reads again.
            shutil.rmtree(call_work, ignore_errors=True)

    return merge_into_turns(
        [s for s in segments if s.speaker == "agent"],
        [s for s in segments if s.speaker == "customer"],
    )


def store_transcript(
    conn: sqlite3.Connection, meta: CallMetadata, turns: list[Turn], provider: str
) -> int:
    """Persist a transcribed call. Call this from a single thread."""
    with conn:
        store.store_call_transcript(
            conn, meta=meta, turns=turns,
            audio_path=f"{meta.call_id}.mp3", provider=provider,
        )
    return len(turns)


def process_call(
    conn: sqlite3.Connection,
    meta: CallMetadata,
    audio_path: Path,
    cache_dir: Path,
    work_dir: Path,
    transcriber: Transcriber | None = None,
    force: bool = False,
) -> int:
    """Transcribe one call and persist it. Returns the number of turns stored.

    Safe to re-run: a cached transcript is reused rather than re-fetched, so a
    re-run costs no API credit and no compute for calls already done.
    """
    transcriber = transcriber or get_transcriber()
    turns = transcribe_call(meta, audio_path, cache_dir, work_dir, transcriber, force)
    return store_transcript(conn, meta, turns, transcriber.name)


def audio_path_for(data_dir: Path, call_id: str) -> Path:
    return data_dir / "audio" / f"{call_id}.mp3"


def default_dirs() -> tuple[Path, Path, Path]:
    """(data_dir, cache_dir, work_dir) from configuration."""
    data_dir = Path(settings.data_dir)
    cache_dir, work_dir = store.init_data_dirs(data_dir)
    return data_dir, cache_dir, work_dir
