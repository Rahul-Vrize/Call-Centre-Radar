"""The needs-attention score (0-100) is computed, not asked-for as a number.
The LLM only narrates the contributing factors; this module owns the
arithmetic so the score stays explainable and reproducible."""
from dataclasses import dataclass

from app.pipeline.reasoning import RawEvidence

# Escalation lexicon — each hit is itself evidence (turn_id + quote) for its factor.
ESCALATION_PHRASES = [
    "speak to a manager",
    "cancel my account",
    "unacceptable",
    "lawsuit",
    "file a complaint",
    "this is the third time",
]


@dataclass
class AttentionFactor:
    factor: str
    weight: float
    evidence: RawEvidence | None = None


def compute_attention_score(
    worst_mood_score: float,
    mood_shift_count: int,
    resolution_status: str,
    escalation_hits: list[AttentionFactor],
    handle_time_seconds: float,
    median_handle_time_seconds: float,
    is_repeat_contact: bool,
) -> tuple[int, list[AttentionFactor]]:
    """Weighted composite -> (score, factors). Documented weights, not a
    single opaque LLM-provided number."""
    raise NotImplementedError
