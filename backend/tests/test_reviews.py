"""Manager triage: the log is append-only, and it never touches the model's work.

Two properties matter more than the endpoint returning 200, and both are the
kind that decay silently under later edits:

  1. **Undo appends, it does not erase.** Reopening a call must leave the
     original closure in the history. A triage record that can be quietly
     rewritten is not evidence of anything, which would undercut the one claim
     this whole system is built on.

  2. **Reviewing never mutates `calls.resolution_status`.** That column is the
     model's judgment and the input to every resolution rate, agent gap and
     failing-issue number on the dashboard. If a manager's click reached it,
     the corpus statistics would start reporting who clicked what.
"""
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.api.reviews import REVIEWED_CALL_IDS, review_state
from app.db.session import SCHEMA_PATH, get_db
from app.main import app


@pytest.fixture
def conn(tmp_path):
    db = sqlite3.connect(tmp_path / "t.db", check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA_PATH.read_text())
    db.executescript(
        """
        INSERT INTO customers (id, name) VALUES ('c1', 'Ada');
        INSERT INTO agents (id, name) VALUES ('a1', 'Grace');
        INSERT INTO calls (id, customer_id, agent_id, started_at, duration_seconds,
                           audio_path, transcript_provider, resolution_status,
                           attention_score, analyzed_at)
        VALUES ('call1', 'c1', 'a1', '2020-06-02T01:00:00', 60, 'call1.mp3',
                'assemblyai', 'unresolved', 40, '2020-06-02T02:00:00');
        INSERT INTO calls (id, customer_id, agent_id, started_at, duration_seconds,
                           audio_path, transcript_provider, resolution_status,
                           attention_score, analyzed_at)
        VALUES ('call2', 'c1', 'a1', '2020-06-02T01:05:00', 60, 'call2.mp3',
                'assemblyai', 'unresolved', 38, '2020-06-02T02:00:00');
        """
    )
    db.commit()
    yield db
    db.close()


@pytest.fixture
def client(conn):
    app.dependency_overrides[get_db] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_a_new_call_has_no_review(client):
    r = client.get("/calls/call1/review")
    assert r.status_code == 200
    assert r.json()["is_reviewed"] is False
    assert r.json()["history"] == []


def test_marking_reviewed_records_who_and_when(client):
    r = client.post(
        "/calls/call1/review",
        json={"action": "reviewed", "reviewer": "Priya",
              "note": "chased the transfer manually"},
    )
    assert r.status_code == 200
    state = r.json()
    assert state["is_reviewed"] is True
    assert state["reviewed_by"] == "Priya"
    assert state["note"] == "chased the transfer manually"
    assert state["reviewed_at"]


def test_undo_appends_rather_than_erasing(client):
    """The whole reason this is a log and not a boolean column."""
    client.post("/calls/call1/review",
                json={"action": "reviewed", "reviewer": "Priya", "note": "handled"})
    r = client.post("/calls/call1/review",
                    json={"action": "reopened", "reviewer": "Sam", "note": "not fixed"})

    state = r.json()
    assert state["is_reviewed"] is False, "reopening must clear the current state"

    # ...but the closure is still on the record, with its author and reason.
    assert len(state["history"]) == 2
    assert [h["action"] for h in state["history"]] == ["reopened", "reviewed"]
    assert state["history"][1]["reviewer"] == "Priya"
    assert state["history"][1]["note"] == "handled"


def test_close_reopen_close_keeps_every_event(client):
    for action, who in [("reviewed", "A"), ("reopened", "B"), ("reviewed", "C")]:
        client.post("/calls/call1/review",
                    json={"action": action, "reviewer": who})
    state = client.get("/calls/call1/review").json()
    assert state["is_reviewed"] is True
    assert [h["reviewer"] for h in state["history"]] == ["C", "B", "A"]


def test_reviewing_never_touches_the_models_resolution_status(client, conn):
    """A manager's click must not rewrite the corpus statistics."""
    before = conn.execute(
        "SELECT resolution_status FROM calls WHERE id = 'call1'"
    ).fetchone()[0]

    client.post("/calls/call1/review",
                json={"action": "reviewed", "reviewer": "Priya"})

    after = conn.execute(
        "SELECT resolution_status FROM calls WHERE id = 'call1'"
    ).fetchone()[0]
    assert after == before == "unresolved"


def test_repeating_the_current_state_is_rejected(client):
    client.post("/calls/call1/review",
                json={"action": "reviewed", "reviewer": "Priya"})
    r = client.post("/calls/call1/review",
                    json={"action": "reviewed", "reviewer": "Priya"})
    assert r.status_code == 409
    assert len(client.get("/calls/call1/review").json()["history"]) == 1


def test_an_unattributed_review_is_refused(client):
    r = client.post("/calls/call1/review",
                    json={"action": "reviewed", "reviewer": "   "})
    assert r.status_code == 422


def test_reviewing_an_unknown_call_is_404(client):
    r = client.post("/calls/nope/review",
                    json={"action": "reviewed", "reviewer": "Priya"})
    assert r.status_code == 404


def test_reviewed_calls_leave_the_attention_queue(client):
    before = client.get("/attention?date=2020-06-02").json()
    assert {c["id"] for c in before["calls"]} == {"call1", "call2"}
    assert before["reviewed_count"] == 0

    client.post("/calls/call1/review",
                json={"action": "reviewed", "reviewer": "Priya"})

    after = client.get("/attention?date=2020-06-02").json()
    assert {c["id"] for c in after["calls"]} == {"call2"}
    assert after["reviewed_count"] == 1

    # ...and come back when someone asks to audit what was done.
    audit = client.get("/attention?date=2020-06-02&include_reviewed=true").json()
    assert {c["id"] for c in audit["calls"]} == {"call1", "call2"}
    assert [c["is_reviewed"] for c in audit["calls"] if c["id"] == "call1"] == [True]


def test_reopening_puts_the_call_back_in_the_queue(client):
    client.post("/calls/call1/review",
                json={"action": "reviewed", "reviewer": "Priya"})
    client.post("/calls/call1/review",
                json={"action": "reopened", "reviewer": "Sam"})

    listed = client.get("/attention?date=2020-06-02").json()
    assert {c["id"] for c in listed["calls"]} == {"call1", "call2"}
    assert listed["reviewed_count"] == 0


def test_reviewed_call_ids_reads_only_the_latest_event(conn):
    """The shared SQL must fold the log, not match any historical row."""
    conn.executescript(
        """
        INSERT INTO call_reviews (call_id, action, reviewer, note, created_at)
        VALUES ('call1', 'reviewed', 'A', '', '2020-06-02T03:00:00');
        INSERT INTO call_reviews (call_id, action, reviewer, note, created_at)
        VALUES ('call1', 'reopened', 'B', '', '2020-06-02T04:00:00');
        """
    )
    conn.commit()
    ids = {r[0] for r in conn.execute(REVIEWED_CALL_IDS)}
    assert ids == set(), "a reopened call must not count as reviewed"

    assert review_state(conn, "call1").is_reviewed is False
