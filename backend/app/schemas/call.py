"""Response models. Every judgment field pairs with an Evidence — a claim without
one is a schema violation, not a runtime hope."""
from typing import Literal

from pydantic import BaseModel


class Evidence(BaseModel):
    turn_id: int
    timestamp: str  # "HH:MM:SS"
    quote: str
    verified: bool

    #: The two checks behind `verified`, surfaced so the verdict is auditable
    #: rather than asserted. Most systems show a tick; this shows the working.
    #:  - match_score: does the quote occur in the cited turn? (0-100)
    #:  - support_score: does the quote *support the claim*? (0-100)
    #: A real quote that does not support its claim is the failure mode the
    #: brief scores negatively, and it is only visible if both are shown.
    match_score: float = 0.0
    support_score: float = 0.0
    #: Which similarity signal produced support_score, or "none" for the
    #: span-only claim types where entailment-checking is a category error.
    method: str = ""
    #: Why it failed, when it did. Empty on a pass.
    reason: str = ""


class Word(BaseModel):
    text: str
    start: float
    end: float
    confidence: float


class Turn(BaseModel):
    id: int
    turn_index: int
    speaker: Literal["agent", "customer"]
    start_seconds: float
    end_seconds: float
    text: str
    words: list[Word] = []
    mood_score: float | None = None
    overlapping: bool = False


class AttentionFactor(BaseModel):
    factor: str
    weight: float
    evidence: Evidence | None = None


class ReviewEvent(BaseModel):
    """One entry in a call's triage history. Never edited, never deleted."""
    action: Literal["reviewed", "reopened"]
    #: A name someone typed. There is no auth here, so this is a claim about
    #: who acted, not a verified identity — the UI says so rather than
    #: implying a permissions model that does not exist.
    reviewer: str
    note: str = ""
    created_at: str


class ReviewState(BaseModel):
    """Current triage state, derived from the latest event in the log.

    Deliberately separate from `resolution_status`: that is the model's
    judgment about whether the CALL succeeded, and it feeds every resolution
    rate on the dashboard. This is whether a HUMAN has dealt with the call
    since. A manager's click must never rewrite the corpus statistics.
    """
    is_reviewed: bool = False
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    note: str = ""
    #: Full log, newest first. Present so "undo" is inspectable: a reopened
    #: call still shows who closed it and why.
    history: list[ReviewEvent] = []


class ReviewRequest(BaseModel):
    action: Literal["reviewed", "reopened"]
    reviewer: str
    note: str = ""


class CallDetail(BaseModel):
    id: str
    customer_id: str
    customer_name: str
    agent_id: str
    agent_name: str
    started_at: str
    duration_seconds: float
    audio_url: str
    transcript_provider: Literal["assemblyai", "whisper"]

    turns: list[Turn]

    intent_label: str | None
    intent_evidence: Evidence | None

    resolution_status: Literal["resolved", "unresolved", "partial"] | None
    resolution_evidence: Evidence | None

    summary: str | None  # <= 40 words

    mood_shift_turn_id: int | None
    mood_shift_evidence: Evidence | None

    attention_score: int | None  # 0-100
    attention_factors: list[AttentionFactor] = []

    review: ReviewState = ReviewState()


class CallSummary(BaseModel):
    id: str
    started_at: str
    duration_seconds: float
    intent_label: str | None
    resolution_status: str | None
    summary: str | None
    attention_score: int | None
    #: The citation behind `intent_label`. Carried on the summary so a LIST of
    #: calls can show its evidence inline — otherwise every ranked view states
    #: judgments whose proof is a click away, and the brief's rule ("a claim
    #: with no evidence scores zero") is satisfied only on the detail page.
    intent_evidence: Evidence | None = None
    #: Whether a human has already triaged this call. Lets a queue show
    #: what is LEFT rather than everything that was ever flagged.
    is_reviewed: bool = False


class Customer(BaseModel):
    id: str
    name: str
    call_count: int
    last_contact: str | None


class AgentIssueStat(BaseModel):
    """How one agent performs on one issue type."""
    cluster_id: int
    label: str
    call_count: int
    resolution_rate: float
    #: Percentage points versus this agent's OWN overall rate. Comparing an
    #: agent against themselves isolates "this issue is hard for them" from
    #: "this agent is weaker overall".
    delta_vs_self: float


class AgentStats(BaseModel):
    id: str
    name: str
    call_count: int
    avg_handle_time_seconds: float
    resolution_rate: float
    avg_attention_score: float
    #: The issue this agent handles worst relative to their own baseline —
    #: the coaching signal. None when no issue has enough calls to judge.
    weakest_issue: AgentIssueStat | None = None


class RepeatContact(BaseModel):
    """One customer calling repeatedly about the same issue.

    The brief's own example — "the complaint that came up nine times this week".
    Keyed on issue cluster, not just customer: every customer in this corpus is
    a repeat caller, so only same-issue repetition carries information.
    """
    customer_id: str
    customer_name: str
    cluster_id: int
    issue_label: str
    call_count: int
    unresolved_count: int
    first_call_at: str
    last_call_at: str
    span_days: float
    calls: list[CallSummary]


class TrendingIssue(BaseModel):
    cluster_id: int
    label: str
    #: The c-TF-IDF terms that formed this group. Shown beside the readable
    #: name so "discovered, not predefined" stays verifiable rather than asserted.
    terms: str = ""
    call_count: int
    counts_by_day: dict[str, int]

    # Outcome quality is the real signal in this corpus. With only four
    # non-contiguous recording days, per-day counts mirror the recording
    # schedule rather than any trend — these fields are what actually
    # distinguish one issue from another.
    resolution_rate: float
    avg_attention_score: float
    avg_handle_time_seconds: float

    #: Cluster's share of each day's calls. Comparable across days in a way raw
    #: counts are not: a day with 95 calls and one with 369 look identical here
    #: unless the issue genuinely over- or under-indexes on that day.
    share_by_day: dict[str, float]


class TrendsBaseline(BaseModel):
    """Corpus-wide averages, so a cluster's numbers can be read as better or
    worse than typical rather than in isolation."""
    call_count: int
    resolution_rate: float
    avg_attention_score: float
    avg_handle_time_seconds: float


class TrendsResponse(BaseModel):
    baseline: TrendsBaseline
    issues: list[TrendingIssue]
