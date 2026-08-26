"""Writes into SQLite. The API never calls anything in here — only the pipeline
does. Every function is idempotent so re-running the batch over already-ingested
calls is safe and cheap.
"""
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from app.pipeline.metadata import CallMetadata
from app.pipeline.turns import Turn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_customer(conn: sqlite3.Connection, meta: CallMetadata) -> None:
    conn.execute(
        "INSERT INTO customers (id, name) VALUES (?, ?) ON CONFLICT(id) DO NOTHING",
        (meta.customer_id, meta.customer_name),
    )


def upsert_agent(conn: sqlite3.Connection, meta: CallMetadata) -> None:
    conn.execute(
        "INSERT INTO agents (id, name) VALUES (?, ?) ON CONFLICT(id) DO NOTHING",
        (meta.agent_id, meta.agent_name),
    )


def is_transcribed(
    conn: sqlite3.Connection, call_id: str, provider: str | None = None
) -> bool:
    """Has this call been transcribed — and if `provider` is given, by THAT
    provider?

    The provider check matters when upgrading. A corpus transcribed offline with
    faster-whisper is already marked done, so a later AssemblyAI run would skip
    every call and silently leave the whole dataset at fallback quality. Treating
    a provider change as "not yet transcribed" makes the upgrade automatic, and
    it stays cheap because the on-disk cache is keyed by provider too.
    """
    row = conn.execute(
        "SELECT transcribed_at, transcript_provider FROM calls WHERE id = ?",
        (call_id,),
    ).fetchone()
    if not row or not row["transcribed_at"]:
        return False
    if provider is not None and row["transcript_provider"] != provider:
        return False
    return True


def store_call_transcript(
    conn: sqlite3.Connection,
    meta: CallMetadata,
    turns: list[Turn],
    audio_path: str,
    provider: str,
) -> None:
    """Persist a call and its turns. Replaces any previous transcript for the
    call so re-transcribing with a different provider is a clean overwrite
    rather than a duplicate set of turns."""
    upsert_customer(conn, meta)
    upsert_agent(conn, meta)

    conn.execute(
        """
        INSERT INTO calls (id, customer_id, agent_id, started_at, duration_seconds,
                           audio_path, transcript_provider, session, caller_mos,
                           transcribed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            audio_path          = excluded.audio_path,
            transcript_provider = excluded.transcript_provider,
            transcribed_at      = excluded.transcribed_at
        """,
        (
            meta.call_id, meta.customer_id, meta.agent_id, meta.started_at,
            meta.duration_seconds, audio_path, provider, meta.session,
            meta.caller_mos, _now(),
        ),
    )

    # Turn ids are referenced by evidence rows, so a re-transcribe must clear
    # the stale citations too rather than leave them pointing at deleted turns.
    conn.execute("DELETE FROM evidence WHERE call_id = ?", (meta.call_id,))
    conn.execute("DELETE FROM turns WHERE call_id = ?", (meta.call_id,))

    conn.executemany(
        """
        INSERT INTO turns (call_id, turn_index, speaker, start_seconds,
                           end_seconds, text, words_json, overlapping)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                meta.call_id, i, t.speaker, t.start, t.end, t.text,
                json.dumps([asdict(w) for w in t.words]), int(t.overlapping),
            )
            for i, t in enumerate(turns)
        ],
    )


def init_data_dirs(data_dir: Path) -> tuple[Path, Path]:
    """Transcript cache and scratch space for split channels."""
    cache_dir = data_dir / "cache"
    work_dir = data_dir / "work"
    cache_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir, work_dir
