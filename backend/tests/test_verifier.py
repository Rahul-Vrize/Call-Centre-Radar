from app.pipeline.verifier import verify_evidence


def test_exact_quote_verifies():
    result = verify_evidence(
        quote="I want to speak to a manager",
        turn_text="Okay I want to speak to a manager right now please",
    )
    assert result.verified


def test_fabricated_quote_fails():
    result = verify_evidence(
        quote="I am extremely happy with this service",
        turn_text="This is the third time I've called about the same charge",
    )
    assert not result.verified
