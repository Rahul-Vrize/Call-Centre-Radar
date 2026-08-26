from app.pipeline.transcribe.base import Segment, Word
from app.pipeline.turns import merge_into_turns, split_on_pauses


def w(text: str, start: float, end: float) -> Word:
    return Word(text=text, start=start, end=end, confidence=0.9)


def test_merges_consecutive_same_speaker_segments():
    agent = [
        Segment(speaker="agent", start=0.0, end=1.5, text="Hello,"),
        Segment(speaker="agent", start=1.7, end=3.0, text="how can I help?"),
    ]
    customer = [Segment(speaker="customer", start=3.5, end=5.0, text="I have a problem.")]

    turns = merge_into_turns(agent, customer)

    assert len(turns) == 2
    assert turns[0].speaker == "agent"
    assert turns[0].text == "Hello, how can I help?"
    assert turns[0].end == 3.0
    assert turns[1].speaker == "customer"


def test_flags_crosstalk_without_merging():
    agent = [Segment(speaker="agent", start=0.0, end=4.0, text="Let me just check that for you")]
    customer = [Segment(speaker="customer", start=2.0, end=3.0, text="no wait I already paid")]

    turns = merge_into_turns(agent, customer)

    assert len(turns) == 2
    assert turns[0].overlapping is True
    assert turns[1].overlapping is True


def test_does_not_merge_across_speaker_change():
    agent = [Segment(speaker="agent", start=0.0, end=1.0, text="Hi")]
    customer = [Segment(speaker="customer", start=1.1, end=2.0, text="Hi")]
    agent2 = [Segment(speaker="agent", start=2.2, end=3.0, text="How can I help?")]

    turns = merge_into_turns(agent + agent2, customer)

    assert [t.speaker for t in turns] == ["agent", "customer", "agent"]


def test_splits_a_segment_at_an_internal_silence():
    """ASR segment boundaries are not turn boundaries. Each channel is
    transcribed in isolation, so the model never sees the pause where the other
    party spoke — it emits one long segment across it."""
    seg = Segment(
        speaker="customer", start=0.0, end=20.0,
        text="I lost my card My credit card",
        words=[w("I", 0.0, 0.3), w("lost", 0.3, 0.7), w("my", 0.7, 0.9), w("card", 0.9, 1.4),
               # 10s of silence — the agent was talking here
               w("My", 11.4, 11.7), w("credit", 11.7, 12.1), w("card", 12.1, 12.6)],
    )

    pieces = split_on_pauses([seg])

    assert len(pieces) == 2
    assert pieces[0].text == "I lost my card"
    assert pieces[0].start == 0.0
    assert pieces[0].end == 1.4
    assert pieces[1].text == "My credit card"
    assert pieces[1].start == 11.4
    assert pieces[1].end == 12.6


def test_pause_splitting_makes_the_conversation_interleave():
    """The regression this was written for: without splitting, the customer's
    whole side collapses into one blob and the agent's replies land after it,
    so the transcript no longer reads turn by turn."""
    customer = [
        Segment(
            speaker="customer", start=0.0, end=12.6,
            text="I lost my card My credit card",
            words=[w("I", 0.0, 0.3), w("lost", 0.3, 0.7), w("my", 0.7, 0.9), w("card", 0.9, 1.4),
                   w("My", 11.4, 11.7), w("credit", 11.7, 12.1), w("card", 12.1, 12.6)],
        )
    ]
    agent = [
        Segment(
            speaker="agent", start=3.0, end=6.0, text="Which card?",
            words=[w("Which", 3.0, 3.4), w("card?", 3.4, 6.0)],
        )
    ]

    turns = merge_into_turns(agent, customer)

    assert [t.speaker for t in turns] == ["customer", "agent", "customer"]
    assert turns[0].text == "I lost my card"
    assert turns[2].text == "My credit card"


def test_segments_without_word_timings_pass_through():
    seg = Segment(speaker="agent", start=0.0, end=5.0, text="no words here")
    assert split_on_pauses([seg]) == [seg]
