from app.pipeline.transcribe.base import Segment
from app.pipeline.turns import merge_into_turns


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
