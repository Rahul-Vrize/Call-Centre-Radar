"""Mood as a measured time series.

Per customer turn, a score in [-1, 1] fusing what was said with how it was said.
This same series draws the dashboard's mood timeline AND feeds the change-point
detector, so the chart and the cited "why" are one computation rather than two
that can disagree.

Two deliberate choices, both documented rather than tuned into a black box:

1. **No pitch tracking, no speech-emotion model.** Every open SER model
   (wav2vec2/IEMOCAP/RAVDESS) is trained on clean 16 kHz *acted studio* speech.
   This corpus is 8 kHz telephony at 48 kbps, and is itself scripted. Neither
   transfers. `librosa.pyin` on codec-degraded 8 kHz is slow and noisy on top.

2. **Prosody comes from word timestamps, not audio.** Speaking rate and pause
   behaviour are already in the ASR output, free and exact. That means mood
   scoring needs no audio decode at all — the whole stage runs in milliseconds
   per call instead of seconds.

Prosody is self-normalised: each customer is compared against their OWN median
speaking rate within the same call, never against a global baseline. Absolute
rate says more about a person than their mood; a change relative to how they
started the call is the signal.
"""
import statistics
from dataclasses import dataclass

from app.pipeline.turns import Turn

#: Fusion weights. Text carries most of the signal on this corpus — the calls
#: are scripted, so the words are far more informative than the delivery.
TEXT_WEIGHT = 0.7
PROSODY_WEIGHT = 0.3

#: A gap longer than this between words is a hesitation, not natural rhythm.
PAUSE_SECONDS = 0.45

#: Escalation phrases. Each hit is itself citable evidence (turn + quote) for
#: the attention score, so this list is shared with attention_score.py.
ESCALATION_PHRASES = (
    "speak to a manager",
    "speak to your manager",
    "talk to a manager",
    "supervisor",
    "cancel my account",
    "close my account",
    "unacceptable",
    "ridiculous",
    "lawsuit",
    "lawyer",
    "file a complaint",
    "third time",
    "fourth time",
    "again and again",
    "still waiting",
    "no one has",
    "nobody has",
)


@dataclass
class ProsodyFeatures:
    words_per_second: float
    pause_ratio: float          # fraction of the turn spent in pauses
    rate_ratio: float           # vs this customer's own median in this call


@dataclass
class MoodPoint:
    turn_index: int
    seconds: float
    text_score: float
    prosody_score: float
    score: float                # the fused value stored on the turn


def _lazy_analyzer():
    """VADER is lexicon-based: deterministic, instant, no model download, and
    fully explainable — you can point at the word that moved the score, which
    matters more here than a couple of points of accuracy from a transformer."""
    global _ANALYZER
    try:
        return _ANALYZER
    except NameError:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        _ANALYZER = SentimentIntensityAnalyzer()
        return _ANALYZER


def text_sentiment_score(text: str) -> float:
    """Valence in [-1, 1]. Negative is unhappy."""
    if not text.strip():
        return 0.0
    return float(_lazy_analyzer().polarity_scores(text)["compound"])


def extract_prosody(turn: Turn, median_rate: float) -> ProsodyFeatures:
    """Rate and pause behaviour, derived purely from word timestamps."""
    duration = max(turn.end - turn.start, 1e-6)
    n_words = len(turn.words) or len(turn.text.split())
    wps = n_words / duration

    pause_total = 0.0
    for prev, word in zip(turn.words, turn.words[1:]):
        gap = word.start - prev.end
        if gap > PAUSE_SECONDS:
            pause_total += gap

    return ProsodyFeatures(
        words_per_second=wps,
        pause_ratio=min(pause_total / duration, 1.0),
        rate_ratio=wps / median_rate if median_rate > 0 else 1.0,
    )


def prosody_valence(features: ProsodyFeatures) -> float:
    """Map delivery onto the same [-1, 1] valence axis as the text score.

    Speaking markedly faster than your own baseline reads as agitation;
    unusually long pauses read as hesitation or frustration. Both push
    negative. Clamped so a single odd turn can't dominate the series.
    """
    rate_effect = -(features.rate_ratio - 1.0)      # faster than baseline -> negative
    pause_effect = -features.pause_ratio
    return max(-1.0, min(1.0, 0.6 * rate_effect + 0.4 * pause_effect))


def fused_mood_score(text_score: float, prosody: float) -> float:
    return max(-1.0, min(1.0, TEXT_WEIGHT * text_score + PROSODY_WEIGHT * prosody))


def score_customer_turns(turns: list[Turn]) -> list[MoodPoint]:
    """Score every customer turn in a call. Agent turns are not scored — the
    brief asks about the customer's mood."""
    customer = [(i, t) for i, t in enumerate(turns) if t.speaker == "customer"]
    if not customer:
        return []

    rates = []
    for _, t in customer:
        duration = max(t.end - t.start, 1e-6)
        n_words = len(t.words) or len(t.text.split())
        rates.append(n_words / duration)
    median_rate = statistics.median(rates) if rates else 0.0

    points: list[MoodPoint] = []
    for idx, turn in customer:
        text_score = text_sentiment_score(turn.text)
        prosody = prosody_valence(extract_prosody(turn, median_rate))
        points.append(
            MoodPoint(
                turn_index=idx,
                seconds=turn.start,
                text_score=text_score,
                prosody_score=prosody,
                score=fused_mood_score(text_score, prosody),
            )
        )
    return points


def escalation_hits(turns: list[Turn]) -> list[tuple[int, str]]:
    """(turn_index, phrase) for every escalation phrase a customer used.

    Returned with the turn index so each hit can be cited, not just counted.
    """
    hits: list[tuple[int, str]] = []
    for i, turn in enumerate(turns):
        if turn.speaker != "customer":
            continue
        lowered = turn.text.lower()
        for phrase in ESCALATION_PHRASES:
            if phrase in lowered:
                hits.append((i, phrase))
    return hits
