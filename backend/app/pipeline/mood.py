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
import re
import statistics
from dataclasses import dataclass

from app.pipeline.turns import Turn

#: Fusion weights. Text carries most of the signal on this corpus — the calls
#: are scripted, so the words are far more informative than the delivery.
TEXT_WEIGHT = 0.7
PROSODY_WEIGHT = 0.3

#: A gap longer than this between words is a hesitation, not natural rhythm.
PAUSE_SECONDS = 0.45

#: Below this many words, a turn gets no mood score at all — not a neutral one.
#:
#: Measured on this corpus, the per-call *worst* mood turn was under 5 words in
#: 67% of calls, and those turns were: 'Certainly.', 'You as well.', 'Hi,',
#: 'All right.', 'Savings?'. Neither half of the signal survives at that length.
#: VADER reads the "no" in "no thank you" as anger (-0.49) when it is a polite
#: decline; and a one-word turn's words-per-second is noise against the
#: speaker's median, so a brisk "Hi," registers as agitation. Fused, these
#: produced a "sustained negative customer mood" factor on 88% of calls — a
#: claim that discriminates nothing and, worse, cannot be honestly cited: a
#: quote of 'Certainly.' offered as proof of a negative mood is evidence that
#: does not support the claim, which the brief scores NEGATIVE.
#:
#: A short turn has *unknown* mood, not neutral mood, so it is excluded from the
#: series rather than scored zero — averaging in fake neutrality would drag the
#: change-point detector just as badly.
#:
#: This is deliberately the same floor the evidence verifier uses for quote
#: length (`evidence_min_quote_words`), which buys a guarantee: every point in
#: the mood series is long enough to quote, so every mood claim is citable by
#: construction.
MIN_MOOD_WORDS = 5

#: …unless the words themselves are unambiguous. "This is absolutely
#: unacceptable" is four words and nobody needs context to read it.
#:
#: The floor above exists because short turns carry no *reliable* signal, not
#: because short turns can never matter. Measured with VADER, the two groups
#: separate cleanly enough to draw a line between them:
#:
#:     unacceptable -0.51   outrageous -0.46   furious -0.57   worst -0.63
#:     'No thanks.' -0.34   'no thank you.' -0.28   'I lost my debit card.' -0.32
#:
#: -0.40 sits in that gap. It admits real anger and still excludes the polite
#: declines and problem-reports that VADER scores negative for the wrong reason.
#: This corpus contains none of the former, so on these 1,441 calls the override
#: never fires — it is here for the recordings that do, a judge's live upload
#: among them.
#:
#: Note this is the one path that can put an uncitable turn in the series: a
#: four-word turn cannot satisfy the verifier's five-word quote floor. That is
#: the right trade — the mood *timeline* should show real anger even when the
#: attention factor beneath it has to report "no evidence" and score zero.
STRONG_SENTIMENT = 0.40

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
    measurable: bool = True     # False when the turn is too short to score


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


#: Words VADER treats as negative sentiment when they are usually just refusal.
NEGATION_TOKENS = frozenset(
    {"no", "nope", "nah", "not", "none", "never", "n't", "nothing"}
)


def is_mere_decline(text: str) -> bool:
    """Is this turn negative only because the customer said "no"?

    VADER has no way to tell refusal from displeasure, so "Nope, that's it."
    (-0.25) and "No thanks." (-0.34) score as unhappy customers when they are
    the ordinary way a satisfied one ends a call. Before this check those were
    the entire unverified remainder of the mood factor — the verifier caught
    every one, which is the safety net working, but a claim that has to be
    caught is a claim better not made.

    The test: remove the refusal words and re-score. If what is left is not
    negative, the negativity *was* the refusal. "Nope, that's it." becomes
    "that's it." (neutral) and is dropped; "This is ridiculous" has no refusal
    word to remove, keeps its score, and is kept.
    """
    words = text.split()
    kept = [w for w in words if w.strip(".,!?'\"").lower() not in NEGATION_TOKENS]
    if len(kept) == len(words):
        return False  # nothing to strip, so the negativity came from elsewhere
    if not kept:
        return True  # nothing but refusal
    return text_sentiment_score(" ".join(kept)) > -0.05


def is_scorable(turn: Turn) -> bool:
    """Does this turn carry enough signal to score at all?

    Long enough to be reliable (MIN_MOOD_WORDS), or short but unambiguous
    (STRONG_SENTIMENT). Word count comes from the text rather than the word
    timings so a turn is judged the same way whichever provider transcribed it.
    """
    if len(turn.text.split()) >= MIN_MOOD_WORDS:
        return True
    return abs(text_sentiment_score(turn.text)) >= STRONG_SENTIMENT


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
        measurable=(n_words >= MIN_WORDS_FOR_PROSODY
                    and duration >= MIN_SECONDS_FOR_PROSODY),
    )


#: Below this many words, speaking rate is not measurable.
#:
#: A one-word turn ("Oh," / "Okay,") lasting a fraction of a second computes to
#: 5+ words/sec against a ~2.5 median, so rate_ratio hits 2.0 and the valence
#: clamps to -1.0 — a polite acknowledgement scored as maximum distress. That
#: was 10% of all prosody scores on this corpus, and those turns dominated the
#: fused series because the clamp is the largest value it can take.
#:
#: Short turns now get neutral prosody: their text score still counts, but we
#: don't invent a delivery signal from two syllables.
MIN_WORDS_FOR_PROSODY = 4

#: Likewise, rate over a very short window is dominated by boundary error in
#: the ASR timestamps rather than by how fast someone is talking.
MIN_SECONDS_FOR_PROSODY = 1.2


def prosody_valence(features: ProsodyFeatures) -> float:
    """Map delivery onto the same [-1, 1] valence axis as the text score.

    Speaking markedly faster than your own baseline reads as agitation;
    unusually long pauses read as hesitation or frustration. Both push
    negative. Clamped so a single odd turn can't dominate the series.
    """
    if not features.measurable:
        return 0.0
    rate_effect = -(features.rate_ratio - 1.0)      # faster than baseline -> negative
    pause_effect = -features.pause_ratio
    return max(-1.0, min(1.0, 0.6 * rate_effect + 0.4 * pause_effect))


def fused_mood_score(text_score: float, prosody: float) -> float:
    return max(-1.0, min(1.0, TEXT_WEIGHT * text_score + PROSODY_WEIGHT * prosody))


def score_customer_turns(turns: list[Turn]) -> list[MoodPoint]:
    """Score every customer turn in a call. Agent turns are not scored — the
    brief asks about the customer's mood."""
    customer = [
        (i, t)
        for i, t in enumerate(turns)
        if t.speaker == "customer" and is_scorable(t)
    ]
    if not customer:
        return []

    # Baseline from turns long enough to be measurable — otherwise the median
    # is dragged upward by the same one-word turns we're excluding.
    rates = []
    for _, t in customer:
        duration = max(t.end - t.start, 1e-6)
        n_words = len(t.words) or len(t.text.split())
        if n_words >= MIN_WORDS_FOR_PROSODY and duration >= MIN_SECONDS_FOR_PROSODY:
            rates.append(n_words / duration)
    median_rate = statistics.median(rates) if rates else 0.0

    points: list[MoodPoint] = []
    for idx, turn in customer:
        text_score = text_sentiment_score(turn.text)
        # A refusal is not a mood. Neutralise the text half rather than dropping
        # the turn: the customer did speak, so the series should still have a
        # point there — it just should not read as unhappiness.
        if text_score < 0 and is_mere_decline(turn.text):
            text_score = 0.0
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


#: Turns that carry no mood signal, however they score.
#:
#: Two categories, both measured as false positives on this corpus:
#:
#: * **Closing pleasantries.** VADER scores "Thank you." at +0.53 — the single
#:   largest text signal in a polite banking call. Left in, the biggest
#:   "mood movement" in most calls is the customer saying goodbye, and 37% of
#:   detected shifts landed in the last two turns.
#: * **Filler and dictated data.** "Um,", "Main Street,", "The zip code is
#:   70021." — a customer reading out an address is not an emotional turning
#:   point, but against a series that is otherwise all zeros it reads as one.
#:
#: These stay in the displayed mood timeline; they are only excluded from the
#: series that change-point detection runs on.
_PLEASANTRY = re.compile(
    r"^(no,? )?(thank(s| you)?|thanks so much|thank you (so |very )?much|you too|you as well"
    r"|bye|bye-bye|goodbye|have a (good|great|nice) (day|one)|no problem"
    r"|okay|ok|alright|all right|sure|yeah|yes|no|nope|nah|um+|uh+|mm+|hmm+"
    r"|that'?s (it|all|great|perfect)|nothing else|that'?ll be (it|all))"
    r"[\s.,!]*$",
    re.IGNORECASE,
)

#: A dictated value — address, zip, amount, account number — rather than an
#: opinion. Mostly digits, or a bare noun phrase with no verb.
_DICTATION = re.compile(r"^[^a-zA-Z]*\d[\d\s.,$#-]*$")


def is_substantive(turn: Turn) -> bool:
    """Could this turn plausibly evidence a change in how the customer feels?

    Used to decide which points change-point detection sees. Filtering here
    rather than lowering a threshold keeps the reason explicit: we are not
    saying the shift was small, we are saying the turn cannot carry one.
    """
    text = turn.text.strip()
    if not text:
        return False
    if _PLEASANTRY.match(text) or _DICTATION.match(text):
        return False
    return len(text.split()) >= MIN_WORDS_FOR_PROSODY


def substantive_points(
    points: list["MoodPoint"], turns: list[Turn]
) -> list["MoodPoint"]:
    """The subset of the mood series that change-point detection should run on."""
    return [p for p in points if is_substantive(turns[p.turn_index])]


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
