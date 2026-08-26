from app.pipeline.mood import (
    PROSODY_WEIGHT,
    TEXT_WEIGHT,
    ProsodyFeatures,
    escalation_hits,
    extract_prosody,
    fused_mood_score,
    prosody_valence,
    score_customer_turns,
    text_sentiment_score,
)
from app.pipeline.transcribe.base import Word
from app.pipeline.turns import Turn


def turn(speaker, text, start=0.0, end=5.0, words=None):
    return Turn(speaker=speaker, start=start, end=end, text=text, words=words or [])


def words_at(texts, start, spacing):
    return [
        Word(text=t, start=start + i * spacing, end=start + i * spacing + spacing * 0.8,
             confidence=0.9)
        for i, t in enumerate(texts)
    ]


def test_sentiment_separates_angry_from_happy():
    angry = text_sentiment_score("This is absolutely unacceptable and terrible")
    happy = text_sentiment_score("Thank you so much, that is wonderful news")
    assert angry < 0
    assert happy > 0
    assert happy > angry


def test_sentiment_of_empty_text_is_neutral():
    assert text_sentiment_score("") == 0.0
    assert text_sentiment_score("   ") == 0.0


def test_weights_sum_to_one():
    assert TEXT_WEIGHT + PROSODY_WEIGHT == 1.0


def test_fused_score_is_clamped():
    assert fused_mood_score(-1.0, -1.0) >= -1.0
    assert fused_mood_score(1.0, 1.0) <= 1.0


def test_speaking_faster_than_your_own_baseline_reads_negative():
    """Prosody is self-normalised: a customer is compared against their own
    median rate in the same call, never a global one."""
    fast = ProsodyFeatures(words_per_second=6.0, pause_ratio=0.0, rate_ratio=1.8)
    steady = ProsodyFeatures(words_per_second=3.0, pause_ratio=0.0, rate_ratio=1.0)
    assert prosody_valence(fast) < prosody_valence(steady)


def test_long_pauses_read_negative():
    hesitant = ProsodyFeatures(words_per_second=2.0, pause_ratio=0.6, rate_ratio=1.0)
    fluent = ProsodyFeatures(words_per_second=2.0, pause_ratio=0.0, rate_ratio=1.0)
    assert prosody_valence(hesitant) < prosody_valence(fluent)


def test_prosody_is_derived_from_word_timestamps_not_audio():
    """The whole stage runs without decoding audio — that's why it's fast."""
    t = turn("customer", "one two three four", 0.0, 2.0,
             words=words_at(["one", "two", "three", "four"], 0.0, 0.5))
    features = extract_prosody(t, median_rate=2.0)
    assert features.words_per_second > 0
    assert features.rate_ratio > 0


def test_only_customer_turns_are_scored():
    turns = [
        turn("agent", "How can I help you today?", 0.0, 3.0),
        turn("customer", "This is absolutely unacceptable", 3.5, 6.0),
        turn("agent", "I am sorry to hear that", 6.5, 8.0),
    ]
    points = score_customer_turns(turns)
    assert len(points) == 1
    assert points[0].turn_index == 1
    assert points[0].score < 0


def test_scoring_a_call_with_no_customer_turns_is_safe():
    assert score_customer_turns([turn("agent", "Hello?")]) == []


def test_escalation_hits_are_citable_by_turn():
    turns = [
        turn("agent", "How can I help?"),
        turn("customer", "I want to speak to a manager about this"),
        turn("agent", "Let me transfer you"),
        turn("customer", "This is the third time I have called"),
    ]
    hits = escalation_hits(turns)
    indices = [i for i, _ in hits]

    assert 1 in indices
    assert 3 in indices
    assert 0 not in indices  # agent turns never count


def test_agent_escalation_language_is_ignored():
    """Only the customer escalating matters. An agent saying "manager" while
    offering to transfer is not a red flag."""
    turns = [turn("agent", "I can put you through to a supervisor if you like")]
    assert escalation_hits(turns) == []
