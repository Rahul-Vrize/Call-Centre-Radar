"""The verifier is the rubric made executable:

    "A claim with no evidence scores zero.
     Evidence that does not support the claim scores negative."

These tests cover both halves — especially the second, which is the one most
implementations skip.
"""
from app.pipeline.verifier import normalize, select_quote, verify_evidence

TURN = "Okay I want to speak to a manager right now please this is unacceptable"


def test_a_quote_present_in_the_turn_passes_the_span_check():
    result = verify_evidence(
        quote="I want to speak to a manager",
        turn_text=TURN,
    )
    assert result.verified
    assert result.match_score >= 85


def test_a_fabricated_quote_is_rejected():
    result = verify_evidence(
        quote="I am extremely happy with this excellent service today",
        turn_text="This is the third time I have called about the same charge",
    )
    assert not result.verified
    assert "does not occur" in result.reason


def test_a_too_short_quote_is_rejected_outright():
    """partial_ratio finds the best-matching substring, so a two-word quote
    scores high against almost any text. Length is the only real defence."""
    result = verify_evidence(quote="the card", turn_text=TURN)
    assert not result.verified
    assert "shorter than" in result.reason


def test_punctuation_and_case_do_not_change_the_verdict():
    result = verify_evidence(
        quote="i want to speak to a MANAGER, right now!!",
        turn_text=TURN,
    )
    assert result.verified


def test_normalize_strips_punctuation_and_collapses_whitespace():
    assert normalize("  Hello,   WORLD!!  ") == "hello world"


def test_evidence_that_does_not_support_the_claim_is_rejected():
    """The half that earns negative marks. The quote is genuinely in the turn —
    it just says nothing about the claim being made."""
    turn = "Sure, let me pull up your account details while we wait a moment"
    result = verify_evidence(
        quote="let me pull up your account details while we wait",
        turn_text=turn,
        claim="the customer threatened to sue the bank over a fraudulent charge",
    )
    assert not result.verified
    assert "does not support" in result.reason


def test_evidence_that_does_support_the_claim_passes():
    result = verify_evidence(
        quote="I want to speak to a manager right now please",
        turn_text=TURN,
        claim="the customer asked to escalate to a manager",
    )
    assert result.verified
    assert result.support_score > 0


def test_support_check_is_skipped_when_no_claim_is_given():
    result = verify_evidence(quote="I want to speak to a manager", turn_text=TURN)
    assert result.verified
    assert result.method == "none"


def test_select_quote_returns_verbatim_text_from_the_turn():
    """The quote must be a substring of the real turn — that is what makes
    hallucinated citations structurally impossible."""
    turn = ("Good morning thanks for calling. "
            "I was charged twice for the same order last Tuesday. "
            "Can you look into it please.")
    quote = select_quote(turn, claim="customer disputes a duplicate charge")

    assert quote
    assert normalize(quote) in normalize(turn)


def test_select_quote_handles_a_single_sentence_turn():
    turn = "I lost my credit card"
    assert select_quote(turn, claim="customer lost their card")
