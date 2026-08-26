"""The needs-attention score (0-100) is computed, not asked for.

The LLM narrates *what* went wrong; this module owns the arithmetic that turns
that into a ranking. Two reasons that split matters:

1. **Explainability.** A manager can be shown why a call scored 82, factor by
   factor, each with its own citation. "The model said 82" cannot be audited,
   argued with, or tuned.
2. **Stability.** Asking a model for a number gives you a different number on
   Tuesday. The ranking that drives the whole product should not drift.

Weights are declared here as constants so they can be read, cited on a slide,
and adjusted deliberately rather than discovered by accident.
"""
from dataclasses import dataclass, field

#: Each factor's maximum contribution. They sum to 1.0; the final score is the
#: weighted sum scaled to 0-100.
WEIGHTS = {
    "resolution": 0.30,       # an unresolved issue is the strongest signal
    "mood_severity": 0.20,    # how bad the customer's mood got
    "mood_shift": 0.15,       # a sustained turn for the worse mid-call
    "escalation": 0.20,       # explicit escalation language
    "repeat_contact": 0.10,   # calling again about the same thing
    "handle_time": 0.05,      # unusually long call
}

RESOLUTION_SEVERITY = {"unresolved": 1.0, "partial": 0.5, "resolved": 0.0}

#: A call this many times the median duration counts as a full outlier.
HANDLE_TIME_OUTLIER_RATIO = 2.0


@dataclass
class AttentionFactor:
    factor: str
    weight: float                     # actual contribution, not the cap
    turn_index: int | None = None     # what to cite, if anything
    detail: str = ""


@dataclass
class AttentionResult:
    score: int
    factors: list[AttentionFactor] = field(default_factory=list)


def compute_attention_score(
    resolution_status: str | None,
    worst_mood: float | None,
    mood_shift_delta: float | None,
    escalation_hits: list[tuple[int, str]],
    handle_time_seconds: float,
    median_handle_time_seconds: float,
    is_repeat_contact: bool,
    repeat_count: int = 0,
) -> AttentionResult:
    """Weighted composite -> (0-100, contributing factors).

    Only factors that actually fired are returned, so the UI never shows a list
    padded with zero-weight noise.
    """
    factors: list[AttentionFactor] = []
    total = 0.0

    # --- Resolution -------------------------------------------------------
    severity = RESOLUTION_SEVERITY.get((resolution_status or "").lower(), 0.5)
    if severity > 0:
        contribution = WEIGHTS["resolution"] * severity
        total += contribution
        factors.append(
            AttentionFactor(
                factor=f"issue {resolution_status or 'unknown'}",
                weight=round(contribution, 3),
                detail=f"resolution status: {resolution_status}",
            )
        )

    # --- Mood severity ----------------------------------------------------
    # worst_mood is in [-1, 1]; only negative mood contributes.
    if worst_mood is not None and worst_mood < 0:
        severity = min(abs(worst_mood), 1.0)
        contribution = WEIGHTS["mood_severity"] * severity
        total += contribution
        factors.append(
            AttentionFactor(
                factor="sustained negative customer mood",
                weight=round(contribution, 3),
                detail=f"worst mood score {worst_mood:.2f}",
            )
        )

    # --- Mood shift -------------------------------------------------------
    # Only a shift for the WORSE matters. A call that starts badly and improves
    # is a success story, not something to escalate.
    if mood_shift_delta is not None and mood_shift_delta < 0:
        severity = min(abs(mood_shift_delta), 1.0)
        contribution = WEIGHTS["mood_shift"] * severity
        total += contribution
        factors.append(
            AttentionFactor(
                factor="mood turned negative during the call",
                weight=round(contribution, 3),
                detail=f"mood fell by {abs(mood_shift_delta):.2f}",
            )
        )

    # --- Escalation language ---------------------------------------------
    if escalation_hits:
        # Saturating: three escalation phrases isn't three times as bad as one.
        severity = min(len(escalation_hits) / 2.0, 1.0)
        contribution = WEIGHTS["escalation"] * severity
        total += contribution
        turn_index, phrase = escalation_hits[0]
        factors.append(
            AttentionFactor(
                factor=f'escalation language: "{phrase}"',
                weight=round(contribution, 3),
                turn_index=turn_index,
                detail=f"{len(escalation_hits)} escalation phrase(s)",
            )
        )

    # --- Repeat contact ---------------------------------------------------
    if is_repeat_contact:
        severity = min(repeat_count / 3.0, 1.0) if repeat_count else 1.0
        contribution = WEIGHTS["repeat_contact"] * severity
        total += contribution
        factors.append(
            AttentionFactor(
                factor="repeat contact about the same issue",
                weight=round(contribution, 3),
                detail=f"{repeat_count} prior call(s) on this issue" if repeat_count else "",
            )
        )

    # --- Handle time ------------------------------------------------------
    if median_handle_time_seconds > 0:
        ratio = handle_time_seconds / median_handle_time_seconds
        if ratio > 1.2:
            severity = min((ratio - 1.2) / (HANDLE_TIME_OUTLIER_RATIO - 1.2), 1.0)
            contribution = WEIGHTS["handle_time"] * severity
            total += contribution
            factors.append(
                AttentionFactor(
                    factor="unusually long call",
                    weight=round(contribution, 3),
                    detail=f"{ratio:.1f}x the median handle time",
                )
            )

    factors.sort(key=lambda f: f.weight, reverse=True)
    return AttentionResult(score=int(round(min(total, 1.0) * 100)), factors=factors)
