"""Response models. Every judgment field pairs with an Evidence — a claim without
one is a schema violation, not a runtime hope."""
from typing import Literal

from pydantic import BaseModel


class Evidence(BaseModel):
    turn_id: int
    timestamp: str  # "HH:MM:SS"
    quote: str
    verified: bool  # result of the fuzzy-match check against the transcript


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


class CallSummary(BaseModel):
    id: str
    started_at: str
    duration_seconds: float
    intent_label: str | None
    resolution_status: str | None
    summary: str | None
    attention_score: int | None


class Customer(BaseModel):
    id: str
    name: str
    call_count: int
    last_contact: str | None


class AgentStats(BaseModel):
    id: str
    name: str
    call_count: int
    avg_handle_time_seconds: float
    resolution_rate: float
    avg_attention_score: float


class TrendingIssue(BaseModel):
    cluster_id: int
    label: str
    call_count: int
    counts_by_day: dict[str, int]
