"""Parsing for the dataset's call metadata.

The shape is nested and has three traps that will silently corrupt the customer
list, call history, and repeat-contact detection if you guess at them. All 1,441
files share this exact shape (verified), so parsing can be strict rather than
defensive — a KeyError here means the assumption broke and we want to know.

    {"sid": "004860b1ab2e4c88",
     "start_time_ms": 1590860609249, "end_time_ms": 1590860654497,
     "agent":  {"metadata": {"agent_name": "Robert"},              "speaker_id": 17},
     "caller": {"metadata": {"first and last name": "Mary Smith"}, "speaker_id": 44},
     "labels": {"lhvb_script": 5.0, "caller_mos": 3.0, "agent_mos": 3.0},
     "session": "Little Harper Valley 2"}

Trap 1: the customer name key is literally "first and last name", with spaces.
Trap 2: timestamps are epoch milliseconds, not ISO strings.
Trap 3: speaker_id is NOT a person identifier. "Mary Smith" appears under 14
        different speaker_ids and agent "Robert" under 42 — they are
        crowdworkers reading roles. Identity is keyed on NAME.
"""
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# The literal key in the dataset. Not "name".
CUSTOMER_NAME_KEY = "first and last name"


@dataclass(frozen=True)
class CallMetadata:
    call_id: str
    customer_id: str
    customer_name: str
    agent_id: str
    agent_name: str
    started_at: str            # ISO 8601, UTC
    duration_seconds: float
    session: str | None
    caller_mos: float | None   # audio quality 1-5; low values predict worse WER
    agent_mos: float | None


def slugify(name: str) -> str:
    """Stable, URL-safe id derived from a name.

    Identity is name-based by necessity (see Trap 3), so the id must be a pure
    function of the name — the same person must produce the same id on every
    call, in any order, across re-runs.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "unknown"


def _iso(epoch_ms: int) -> str:
    return datetime.fromtimestamp(epoch_ms / 1000, timezone.utc).isoformat()


def parse_metadata(path: Path) -> CallMetadata:
    raw = json.loads(path.read_text(encoding="utf-8"))

    customer_name = raw["caller"]["metadata"][CUSTOMER_NAME_KEY]
    agent_name = raw["agent"]["metadata"]["agent_name"]
    labels = raw.get("labels") or {}

    start_ms = raw["start_time_ms"]
    end_ms = raw["end_time_ms"]

    return CallMetadata(
        call_id=raw["sid"],
        customer_id=slugify(customer_name),
        customer_name=customer_name,
        agent_id=slugify(agent_name),
        agent_name=agent_name,
        started_at=_iso(start_ms),
        duration_seconds=(end_ms - start_ms) / 1000,
        session=raw.get("session"),
        caller_mos=labels.get("caller_mos"),
        agent_mos=labels.get("agent_mos"),
    )


def iter_metadata(data_dir: Path, limit: int | None = None):
    """Yield CallMetadata for every call that has both metadata and audio.

    Sorted by call id so --limit picks a deterministic subset — the day-one
    throughput test needs to be repeatable.
    """
    meta_dir = data_dir / "metadata"
    audio_dir = data_dir / "audio"

    count = 0
    for meta_path in sorted(meta_dir.glob("*.json")):
        if not (audio_dir / f"{meta_path.stem}.mp3").exists():
            continue
        yield parse_metadata(meta_path)
        count += 1
        if limit is not None and count >= limit:
            return
