"""The rubric, enforced at runtime. "A claim with no evidence scores zero;
evidence that does not support the claim scores negative" — implemented as a
guardrail here, not trusted to a prompt.

Every evidence object the LLM emits is fuzzy-matched against the actual
transcript text in a window around its claimed timestamp before it is ever
stored. A claim that fails is rejected (regenerate) or surfaced to the
dashboard as unverified rather than silently kept.
"""
from dataclasses import dataclass

from app.config import settings


@dataclass
class VerificationResult:
    verified: bool
    match_score: float  # 0-100, from rapidfuzz


def verify_evidence(quote: str, turn_text: str, threshold: int = None) -> VerificationResult:
    """Fuzzy-match `quote` against `turn_text` (the actual transcript content
    at the claimed timestamp +/- a small window)."""
    from rapidfuzz import fuzz

    threshold = threshold if threshold is not None else settings.evidence_match_threshold
    score = fuzz.partial_ratio(quote.lower(), turn_text.lower())
    return VerificationResult(verified=score >= threshold, match_score=score)
