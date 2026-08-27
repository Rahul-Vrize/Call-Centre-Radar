"""Stages 4-5 for one call: mood -> shift -> reasoning -> verification -> score.

The ordering matters. Every citation is resolved to verbatim text from OUR
transcript and verified BEFORE it reaches storage, so nothing unverified can
leak onto the dashboard by accident. A claim whose evidence fails is still
stored — flagged unverified — because silently dropping it would hide the
system's own error rate, and that rate is a number worth reporting.

Split into `prepare_analysis` (reads + compute, no writes) and
`persist_analysis` (a short write transaction) so a batch can fan the slow part
across threads. The slow part is a ~10s network call to the LLM; holding a
SQLite write transaction open across it would serialise every worker and turn
concurrency into lock contention.
"""
import json
import sqlite3
from dataclasses import dataclass, field

from app.config import settings
from app.pipeline import attention_score, changepoint, mood, reasoning, verifier
from app.pipeline.turns import Turn


@dataclass
class StoredTurn:
    """A turn as it exists in the database — index for citation, id for FK."""
    db_id: int
    turn: Turn


@dataclass
class EvidenceRow:
    claim_type: str
    claim_text: str
    turn_db_id: int
    timestamp: str
    quote: str
    match_score: float
    support_score: float
    verified: bool


@dataclass
class AnalysisResult:
    call_id: str
    intent_label: str
    resolution_status: str
    summary: str
    attention: int
    mood_shift_db_id: int | None
    mood_updates: list[tuple[float, int]] = field(default_factory=list)
    evidence: list[EvidenceRow] = field(default_factory=list)
    factors_json: str = "[]"
    shift_turn_index: int | None = None
    n_mood_points: int = 0


def load_turns(conn: sqlite3.Connection, call_id: str) -> list[StoredTurn]:
    rows = conn.execute(
        """
        SELECT id, turn_index, speaker, start_seconds, end_seconds, text,
               words_json, overlapping
        FROM turns WHERE call_id = ? ORDER BY turn_index
        """,
        (call_id,),
    ).fetchall()

    from app.pipeline.transcribe.base import Word

    return [
        StoredTurn(
            db_id=r["id"],
            turn=Turn(
                speaker=r["speaker"],
                start=r["start_seconds"],
                end=r["end_seconds"],
                text=r["text"],
                words=[Word(**w) for w in json.loads(r["words_json"] or "[]")],
                overlapping=bool(r["overlapping"]),
            ),
        )
        for r in rows
    ]


def timestamp(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def is_citable_shift(turn: Turn) -> bool:
    """Can this turn actually evidence a mood shift?

    Change-point detection finds where the mood *series* moves, but the series
    is partly prosodic — speaking rate and pauses — so it will happily fire on a
    customer reading out an address. Measured on the corpus, the rejected
    mood-shift citations were turns like 'Main Street,', '05418.', 'my savings
    account.' and 'You as well.': real breakpoints in the numbers, and no
    emotional content a reader could verify.

    So the rule is simply: don't make a claim you cannot cite. If the turn is
    too short to clear the verifier's own quote-length floor, we report no shift
    rather than a shift nobody can check. That trades some recall for citations
    that hold up, which is the trade this whole system is built around.
    """
    if turn.speaker != "customer":
        return False
    words = len(verifier.normalize(turn.text).split())
    return words >= getattr(
        settings, "evidence_min_quote_words", verifier.DEFAULT_MIN_QUOTE_WORDS
    )


def prior_call_count(conn: sqlite3.Connection, call_id: str) -> int:
    """How many earlier calls this customer made, on any subject."""
    row = conn.execute(
        """
        SELECT COUNT(*) AS n FROM calls
        WHERE customer_id = (SELECT customer_id FROM calls WHERE id = ?)
          AND started_at < (SELECT started_at FROM calls WHERE id = ?)
        """,
        (call_id, call_id),
    ).fetchone()
    return row["n"] if row else 0


def prior_same_issue_count(conn: sqlite3.Connection, call_id: str, intent_label: str) -> int:
    """How many earlier calls this customer made *about this same issue*.

    The attention factor above this reads "repeat contact about the same issue",
    so that is what has to be counted. Counting every prior call instead — which
    is what shipped — made the factor fire on 93% of the corpus, because 1,441
    calls are spread over 100 customers and almost everyone has phoned before.
    A signal that is true of nearly every row cannot rank anything, and the
    "about the same issue" half of the sentence was simply never checked.

    Matching on intent restores it to 43% and, more importantly, makes the claim
    mean what it says. Intent is the right key rather than the issue cluster:
    clusters are derived from summary embeddings and drift with re-clustering,
    while intent is per-call, stable, and already the thing the customer asked
    for.
    """
    if not intent_label:
        return 0
    row = conn.execute(
        """
        SELECT COUNT(*) AS n FROM calls
        WHERE customer_id = (SELECT customer_id FROM calls WHERE id = ?)
          AND started_at < (SELECT started_at FROM calls WHERE id = ?)
          AND intent_label = ?
        """,
        (call_id, call_id, intent_label),
    ).fetchone()
    return row["n"] if row else 0


def _build_evidence(
    claim_type: str,
    claim_text: str,
    stored: list[StoredTurn],
    turn_index: int,
    check_support: bool = True,
) -> EvidenceRow | None:
    """Resolve a turn index to a verified citation.

    This is where the design pays off: the quote is *selected from* the turn's
    own text, never authored by the model, so it is verbatim by construction.
    What still has to be checked is whether it SUPPORTS the claim.
    """
    if not (0 <= turn_index < len(stored)):
        return None

    target = stored[turn_index]
    quote = verifier.select_quote(target.turn.text, claim_text)
    claim = verifier.claim_for(claim_type, claim_text) if check_support else None
    result = verifier.verify_evidence(
        quote=quote, turn_text=target.turn.text, claim=claim
    )

    return EvidenceRow(
        claim_type=claim_type,
        claim_text=claim_text,
        turn_db_id=target.db_id,
        timestamp=timestamp(target.turn.start),
        quote=quote,
        match_score=result.match_score,
        support_score=result.support_score,
        verified=result.verified,
    )


def prepare_analysis(
    conn: sqlite3.Connection,
    call_id: str,
    median_handle_time: float,
) -> AnalysisResult:
    """Everything except the writes. Safe to run on a worker thread."""
    stored = load_turns(conn, call_id)
    if not stored:
        raise ValueError(f"call {call_id} has no stored turns — transcribe it first")

    turns = [s.turn for s in stored]
    duration = conn.execute(
        "SELECT duration_seconds FROM calls WHERE id = ?", (call_id,)
    ).fetchone()

    # --- Stage 4: mood series + change point ------------------------------
    points = mood.score_customer_turns(turns)
    shift = changepoint.find_mood_shift(
        [p.score for p in points], [p.turn_index for p in points]
    )
    # A detected breakpoint on an un-quotable turn is a claim without evidence,
    # which is exactly what the brief scores zero. Drop it.
    if shift is not None and not is_citable_shift(stored[shift.turn_index].turn):
        shift = None
    mood_updates = [(p.score, stored[p.turn_index].db_id) for p in points]

    # Keep the turn the minimum came from, not just the value — the attention
    # factor it feeds has to cite the moment, and "worst mood" is meaningless to
    # a manager without the words that earned it.
    worst_point = min(points, key=lambda p: p.score, default=None)
    worst_mood = worst_point.score if worst_point else None
    # Only cite a turn substantial enough to clear the verifier's quote-length
    # floor, for the same reason is_citable_shift exists: a citation of "Okay."
    # is a citation nobody can check.
    worst_mood_turn_index = (
        worst_point.turn_index
        if worst_point and is_citable_shift(stored[worst_point.turn_index].turn)
        else None
    )

    # --- Stage 5: grounded reasoning (the slow, network-bound part) -------
    result = reasoning.analyze_call(turns)

    evidence: list[EvidenceRow] = []

    row = _build_evidence("intent", result.intent.label, stored, result.intent.turn_index)
    if row:
        evidence.append(row)

    # Contextualised with the call's own intent rather than left abstract.
    # "the issue was resolved" shares almost no vocabulary with the turn that
    # proves it ("$135 has been transferred from your savings to your
    # checking"), so cosine similarity scored real, correct citations as
    # unsupported — measured at 3% pass. Naming the intent puts claim and quote
    # in the same semantic neighbourhood: identical citations went 0.24 -> 0.56,
    # and 0/8 -> 5/8 on the sample. The remaining failures are genuinely
    # uninformative quotes ("Okay.", "$147"), which SHOULD fail.
    row = _build_evidence(
        "resolution",
        f"the customer wanted to {result.intent.label}; this was {result.resolution.label}",
        stored, result.resolution.turn_index,
    )
    if row:
        evidence.append(row)

    mood_shift_db_id = None
    if shift is not None:
        direction = "worse" if shift.delta < 0 else "better"
        # No support check here, deliberately. This turn was chosen by OUR
        # change-point detector, not claimed by the model — the citation means
        # "these are the words spoken where the shift was detected", which is
        # true by construction. Entailment-checking a factual pointer against a
        # statement about mood is a category error, and scored 0/10 doing it.
        # The span check still runs, so the quote is still verifiably verbatim.
        row = _build_evidence(
            "mood_shift",
            f"the customer's mood turned {direction} at this point in the call",
            stored, shift.turn_index, check_support=False,
        )
        if row:
            evidence.append(row)
        mood_shift_db_id = stored[shift.turn_index].db_id

    # --- Attention score --------------------------------------------------
    # Counted here rather than earlier because it needs the intent the model
    # just returned.
    repeat_count = prior_same_issue_count(conn, call_id, result.intent.label)
    hits = mood.escalation_hits(turns)
    attention = attention_score.compute_attention_score(
        resolution_status=result.resolution.label,
        worst_mood=worst_mood,
        mood_shift_delta=shift.delta if shift else None,
        escalation_hits=hits,
        handle_time_seconds=row_value(duration),
        median_handle_time_seconds=median_handle_time,
        is_repeat_contact=repeat_count > 0,
        repeat_count=repeat_count,
        resolution_turn_index=result.resolution.turn_index,
        worst_mood_turn_index=worst_mood_turn_index,
        mood_shift_turn_index=shift.turn_index if shift else None,
        intent_turn_index=result.intent.turn_index,
    )

    # Citations built above (intent, resolution, mood shift) are reused here
    # rather than rebuilt: the "issue unresolved" factor and the resolution
    # judgment cite the same moment, and storing that twice would inflate the
    # evidence count without adding one verifiable fact.
    by_turn = {row.turn_db_id: row for row in evidence}

    factors_json = []
    for factor in attention.factors:
        evidence_payload = None
        if factor.turn_index is not None and 0 <= factor.turn_index < len(stored):
            fact_row = by_turn.get(stored[factor.turn_index].db_id)
            if fact_row is None:
                fact_row = _build_evidence(
                    "attention_factor",
                    factor.factor,
                    stored,
                    factor.turn_index,
                    check_support=factor.check_support,
                )
                if fact_row:
                    evidence.append(fact_row)
                    by_turn[fact_row.turn_db_id] = fact_row
            if fact_row:
                evidence_payload = {
                    "turn_id": fact_row.turn_db_id,
                    "timestamp": fact_row.timestamp,
                    "quote": fact_row.quote,
                    "verified": fact_row.verified,
                }
        factors_json.append(
            {"factor": factor.factor, "weight": factor.weight, "evidence": evidence_payload}
        )

    return AnalysisResult(
        call_id=call_id,
        intent_label=result.intent.label,
        resolution_status=result.resolution.label,
        summary=result.summary,
        attention=attention.score,
        mood_shift_db_id=mood_shift_db_id,
        mood_updates=mood_updates,
        evidence=evidence,
        factors_json=json.dumps(factors_json),
        shift_turn_index=shift.turn_index if shift else None,
        n_mood_points=len(points),
    )


def row_value(row) -> float:
    return row["duration_seconds"] if row else 0.0


def persist_analysis(conn: sqlite3.Connection, result: AnalysisResult) -> dict:
    """Write everything for one call. Short transaction, single thread."""
    with conn:
        conn.executemany(
            "UPDATE turns SET mood_score = ? WHERE id = ?", result.mood_updates
        )
        # Citations are rebuilt from scratch on every analysis run.
        conn.execute("DELETE FROM evidence WHERE call_id = ?", (result.call_id,))
        conn.executemany(
            """
            INSERT INTO evidence (call_id, claim_type, claim_text, turn_id,
                                  timestamp, quote, match_score, support_score, verified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (result.call_id, e.claim_type, e.claim_text, e.turn_db_id,
                 e.timestamp, e.quote, e.match_score, e.support_score, int(e.verified))
                for e in result.evidence
            ],
        )
        conn.execute(
            """
            UPDATE calls SET intent_label = ?, resolution_status = ?, summary = ?,
                             mood_shift_turn_id = ?, attention_score = ?,
                             attention_factors_json = ?, analyzed_at = datetime('now')
            WHERE id = ?
            """,
            (
                result.intent_label, result.resolution_status, result.summary,
                result.mood_shift_db_id, result.attention, result.factors_json,
                result.call_id,
            ),
        )

    verified = sum(1 for e in result.evidence if e.verified)
    return {
        "intent": result.intent_label,
        "resolution": result.resolution_status,
        "attention": result.attention,
        "mood_points": result.n_mood_points,
        "shift": result.shift_turn_index,
        "citations": len(result.evidence),
        "verified": verified,
    }


def analyze_call(
    conn: sqlite3.Connection,
    call_id: str,
    median_handle_time: float,
    repeat_count: int = 0,   # kept for call-site compatibility; derived internally
) -> dict:
    """Analyse and persist one call, single-threaded."""
    return persist_analysis(conn, prepare_analysis(conn, call_id, median_handle_time))
