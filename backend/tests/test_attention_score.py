"""The attention score drives the product's flagship ranking, so its arithmetic
needs to be pinned down — not just "produces a number"."""
import pytest

from app.pipeline.attention_score import WEIGHTS, compute_attention_score


def score(**kwargs) -> int:
    defaults = dict(
        resolution_status="resolved",
        worst_mood=0.0,
        mood_shift_delta=None,
        escalation_hits=[],
        handle_time_seconds=60.0,
        median_handle_time_seconds=60.0,
        is_repeat_contact=False,
    )
    return compute_attention_score(**{**defaults, **kwargs}).score


def test_a_clean_resolved_call_scores_zero():
    assert score() == 0


def test_unresolved_outweighs_partial():
    assert score(resolution_status="unresolved") > score(resolution_status="partial")
    assert score(resolution_status="partial") > score(resolution_status="resolved")


def test_positive_mood_does_not_add_to_the_score():
    """A happy customer is not a reason to escalate."""
    assert score(worst_mood=0.8) == 0


def test_mood_improving_is_not_penalised():
    """A call that starts badly and ends well is a success story. Only a shift
    for the worse should raise the score."""
    assert score(mood_shift_delta=+0.6) == 0
    assert score(mood_shift_delta=-0.6) > 0


def test_escalation_language_saturates():
    """Three escalation phrases is not three times as urgent as one."""
    one = score(escalation_hits=[(3, "speak to a manager")])
    many = score(escalation_hits=[(3, "speak to a manager"), (5, "lawsuit"),
                                  (7, "unacceptable"), (9, "supervisor")])
    assert one > 0
    assert many > one
    assert many <= round(WEIGHTS["escalation"] * 100) + 1


def test_worst_case_call_approaches_100():
    result = compute_attention_score(
        resolution_status="unresolved",
        worst_mood=-1.0,
        mood_shift_delta=-1.0,
        escalation_hits=[(1, "lawsuit"), (2, "speak to a manager")],
        handle_time_seconds=300.0,
        median_handle_time_seconds=60.0,
        is_repeat_contact=True,
        repeat_count=5,
    )
    assert result.score == 100


def test_score_is_bounded():
    assert 0 <= score(resolution_status="unresolved", worst_mood=-5.0) <= 100


def test_factors_are_returned_sorted_and_only_when_they_fire():
    result = compute_attention_score(
        resolution_status="unresolved",
        worst_mood=-0.2,
        mood_shift_delta=None,
        escalation_hits=[],
        handle_time_seconds=60.0,
        median_handle_time_seconds=60.0,
        is_repeat_contact=False,
    )
    names = [f.factor for f in result.factors]
    assert any("unresolved" in n for n in names)
    assert not any("escalation" in n for n in names)  # didn't fire, not listed
    weights = [f.weight for f in result.factors]
    assert weights == sorted(weights, reverse=True)


def test_escalation_factor_carries_a_citable_turn():
    result = compute_attention_score(
        resolution_status="resolved", worst_mood=0.0, mood_shift_delta=None,
        escalation_hits=[(7, "speak to a manager")],
        handle_time_seconds=60.0, median_handle_time_seconds=60.0,
        is_repeat_contact=False,
    )
    factor = next(f for f in result.factors if "escalation" in f.factor)
    assert factor.turn_index == 7


@pytest.mark.parametrize("status", ["resolved", "partial", "unresolved", None])
def test_handles_every_resolution_status(status):
    assert 0 <= score(resolution_status=status) <= 100
