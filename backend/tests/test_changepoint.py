from app.pipeline.changepoint import MIN_POINTS, find_mood_shift, smooth


def indices(n: int) -> list[int]:
    return list(range(n))


def test_too_short_a_series_reports_no_shift():
    """Calls here average 58s and often have 3-5 customer turns. Change-point
    detection on 4 points is numerology — "no shift" is the honest answer."""
    scores = [0.5, -0.5, -0.6]
    assert find_mood_shift(scores, indices(len(scores))) is None


def test_detects_a_sustained_drop():
    scores = [0.6, 0.5, 0.6, 0.5, -0.6, -0.7, -0.6, -0.7]
    shift = find_mood_shift(scores, indices(len(scores)))

    assert shift is not None
    assert shift.delta < 0                 # mood got worse
    assert 3 <= shift.turn_index <= 5      # near the real boundary


def test_detects_a_sustained_improvement_with_positive_delta():
    scores = [-0.7, -0.6, -0.7, -0.6, 0.5, 0.6, 0.5, 0.6]
    shift = find_mood_shift(scores, indices(len(scores)))

    assert shift is not None
    assert shift.delta > 0


def test_a_flat_series_has_no_meaningful_shift():
    scores = [0.1] * 10
    shift = find_mood_shift(scores, indices(10))
    assert shift is None or abs(shift.delta) < 0.1


def test_single_turn_spike_is_not_a_shift():
    """A dip is not a shift. One bad turn in an otherwise steady call should not
    be reported as the moment the mood turned."""
    scores = [0.5, 0.5, 0.5, -0.9, 0.5, 0.5, 0.5, 0.5]
    shift = find_mood_shift(scores, indices(len(scores)))
    assert shift is None or abs(shift.delta) < 0.35


def test_returned_index_maps_back_to_the_callers_turn_numbers():
    """Scores come from customer turns only, so the index must be translated
    back to the real turn number or every citation points at the wrong line."""
    turn_ids = [2, 5, 8, 11, 14, 17, 20, 23]
    scores = [0.6, 0.5, 0.6, 0.5, -0.6, -0.7, -0.6, -0.7]

    shift = find_mood_shift(scores, turn_ids)

    assert shift is not None
    assert shift.turn_index in turn_ids


def test_smooth_preserves_length_and_damps_spikes():
    values = [0.0, 0.0, 1.0, 0.0, 0.0]
    out = smooth(values)
    assert len(out) == len(values)
    assert out[2] < 1.0


def test_mismatched_input_lengths_return_none():
    assert find_mood_shift([0.1] * MIN_POINTS, [0, 1]) is None
