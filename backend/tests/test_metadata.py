"""Guards the three traps in the dataset's metadata schema.

These are regression tests for assumptions that would fail *silently* — a wrong
customer key or a speaker_id-based identity doesn't crash, it just quietly
produces a broken customer list nobody notices until demo day.
"""
import json
from pathlib import Path

import pytest

from app.pipeline.metadata import parse_metadata, slugify

SAMPLE = {
    "sid": "004860b1ab2e4c88",
    "start_time_ms": 1590860609249,
    "end_time_ms": 1590860654497,
    "agent": {"metadata": {"agent_name": "Robert"}, "speaker_id": 17},
    "caller": {"metadata": {"first and last name": "Mary Smith"}, "speaker_id": 44},
    "labels": {"lhvb_script": 5.0, "caller_mos": 3.0, "agent_mos": 3.0},
    "session": "Little Harper Valley 2",
}


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    path = tmp_path / f"{SAMPLE['sid']}.json"
    path.write_text(json.dumps(SAMPLE), encoding="utf-8")
    return path


def test_reads_the_space_separated_customer_name_key(sample_file):
    """Trap 1: the key is literally "first and last name", not "name"."""
    meta = parse_metadata(sample_file)
    assert meta.customer_name == "Mary Smith"
    assert meta.agent_name == "Robert"


def test_converts_epoch_milliseconds_to_iso(sample_file):
    """Trap 2: timestamps are epoch ms, not ISO strings."""
    meta = parse_metadata(sample_file)
    assert meta.started_at.startswith("2020-05-30T")
    assert meta.duration_seconds == pytest.approx(45.248)


def test_identity_is_name_based_not_speaker_id(tmp_path):
    """Trap 3: speaker_id is per-recording, not per-person. The same customer
    appears under 14 different speaker_ids, so identity must key on name or
    every customer's call history shatters into singletons."""
    first = dict(SAMPLE)
    second = json.loads(json.dumps(SAMPLE))
    second["sid"] = "ffffffffffffffff"
    second["caller"]["speaker_id"] = 999  # same person, different recording slot
    second["agent"]["speaker_id"] = 888

    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps(first), encoding="utf-8")
    b.write_text(json.dumps(second), encoding="utf-8")

    meta_a, meta_b = parse_metadata(a), parse_metadata(b)
    assert meta_a.customer_id == meta_b.customer_id == "mary-smith"
    assert meta_a.agent_id == meta_b.agent_id == "robert"


def test_carries_audio_quality_label(sample_file):
    meta = parse_metadata(sample_file)
    assert meta.caller_mos == 3.0
    assert meta.session == "Little Harper Valley 2"


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Mary Smith", "mary-smith"),
        ("  Robert  ", "robert"),
        ("O'Brien-Jones", "o-brien-jones"),
        ("!!!", "unknown"),
    ],
)
def test_slugify_is_stable_and_url_safe(name, expected):
    assert slugify(name) == expected


def test_missing_customer_name_key_fails_loudly(tmp_path):
    """All 1,441 files share one shape. If that ever stops being true we want a
    KeyError, not a call quietly attributed to a customer named None."""
    broken = json.loads(json.dumps(SAMPLE))
    broken["caller"]["metadata"] = {"name": "Mary Smith"}  # plausible, wrong
    path = tmp_path / "broken.json"
    path.write_text(json.dumps(broken), encoding="utf-8")

    with pytest.raises(KeyError):
        parse_metadata(path)
