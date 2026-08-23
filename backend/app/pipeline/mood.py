"""Mood as a measured time series: text sentiment fused with audio prosody on
the customer channel, per turn. This series both draws the UI's mood timeline
and feeds the change-point detector in changepoint.py — the chart and the
"why" are the same computation."""
from dataclasses import dataclass


@dataclass
class ProsodyFeatures:
    pitch_mean: float
    pitch_variance: float
    energy: float
    speaking_rate: float


def extract_prosody(customer_wav_path: str, start: float, end: float) -> ProsodyFeatures:
    """Pull pitch/energy/rate features for one turn's audio window via librosa."""
    raise NotImplementedError


def text_sentiment_score(text: str) -> float:
    """Score in [-1, 1] from a small local emotion/sentiment classifier."""
    raise NotImplementedError


def fused_mood_score(text: str, prosody: ProsodyFeatures) -> float:
    """Documented, transparent weighted combination — not a black box."""
    raise NotImplementedError
