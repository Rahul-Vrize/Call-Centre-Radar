"""Find the point where the customer's mood score genuinely shifts, using
change-point detection (ruptures/PELT) rather than an LLM's opinion. The
shift's turn_id + quote become the evidence for the dashboard's mood chart."""
from dataclasses import dataclass


@dataclass
class MoodShift:
    turn_id: int
    quote: str
    timestamp: str  # "HH:MM:SS"


def find_mood_shift(mood_scores: list[float], turn_ids: list[int]) -> MoodShift | None:
    """Run PELT over the customer mood-score series; return the first
    statistically significant breakpoint, or None if the mood never shifts."""
    raise NotImplementedError
