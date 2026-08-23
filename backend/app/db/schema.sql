-- Precomputed analysis lives here; the API only ever reads it.
-- Every *_evidence_json column stores {"turn_id": int, "t": "HH:MM:SS", "quote": str}
-- (or a list of such objects), already fuzzy-match verified against the transcript.

CREATE TABLE IF NOT EXISTS customers (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agents (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS calls (
    id                        TEXT PRIMARY KEY,
    customer_id               TEXT NOT NULL REFERENCES customers(id),
    agent_id                  TEXT NOT NULL REFERENCES agents(id),
    started_at                TEXT NOT NULL,
    duration_seconds          REAL NOT NULL,
    audio_path                TEXT NOT NULL,
    transcript_provider       TEXT NOT NULL,           -- "assemblyai" | "whisper"

    intent_label              TEXT,
    intent_evidence_json      TEXT,

    resolution_status         TEXT,                     -- "resolved" | "unresolved" | "partial"
    resolution_evidence_json  TEXT,

    summary                   TEXT,                     -- <= 40 words

    mood_shift_turn_id        INTEGER,
    mood_shift_evidence_json  TEXT,

    attention_score           INTEGER,                  -- 0-100
    attention_factors_json    TEXT,                      -- [{factor, weight, evidence?}]

    processed_at              TEXT
);

CREATE TABLE IF NOT EXISTS turns (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id          TEXT NOT NULL REFERENCES calls(id),
    turn_index       INTEGER NOT NULL,
    speaker          TEXT NOT NULL CHECK (speaker IN ('agent', 'customer')),
    start_seconds    REAL NOT NULL,
    end_seconds      REAL NOT NULL,
    text             TEXT NOT NULL,
    words_json       TEXT,                               -- [{text, start, end, confidence}]
    mood_score       REAL,                                -- fused text-sentiment + prosody, customer turns only
    overlapping      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_turns_call_id ON turns(call_id);

CREATE TABLE IF NOT EXISTS issue_clusters (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    label      TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS call_clusters (
    call_id    TEXT NOT NULL REFERENCES calls(id),
    cluster_id INTEGER NOT NULL REFERENCES issue_clusters(id),
    PRIMARY KEY (call_id, cluster_id)
);
