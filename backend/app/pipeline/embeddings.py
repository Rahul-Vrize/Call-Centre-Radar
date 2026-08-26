"""Sentence embeddings, used by two very different consumers:

* verifier.py — does this quote actually *support* this claim?
* clustering.py — which calls are about the same underlying issue?

Uses `fastembed` rather than `sentence-transformers`. Same models (bge-small),
but ONNX-backed instead of torch: ~50MB of dependency instead of ~2.5GB, and
onnxruntime is already in the image for faster-whisper's VAD. On CPU-only
hardware it is also faster.

Everything degrades gracefully. If fastembed isn't installed, similarity falls
back to a lexical measure so the pipeline still runs end to end — worse, but
running and honest about it, rather than crashing the batch.
"""
import logging
from functools import lru_cache

MODEL_NAME = "BAAI/bge-small-en-v1.5"

_UNAVAILABLE = object()


@lru_cache(maxsize=1)
def _model():
    try:
        from fastembed import TextEmbedding

        return TextEmbedding(model_name=MODEL_NAME)
    except Exception as e:
        # Loud, once. A silent fall-through to lexical matching degrades every
        # support check in the run — the citation pass rate drops and nothing
        # in the output says why. Better a warning in the batch log than a
        # quietly worse number on a slide.
        logging.getLogger(__name__).warning(
            "fastembed unavailable (%s: %s) — evidence support checks will fall "
            "back to lexical similarity, which is a materially weaker signal. "
            "Re-run with the model reachable for full-quality verification.",
            type(e).__name__, e,
        )
        return _UNAVAILABLE


def available() -> bool:
    return _model() is not _UNAVAILABLE


def embed(texts: list[str]) -> list[list[float]] | None:
    """Embeddings for a batch, or None if the model isn't available."""
    model = _model()
    if model is _UNAVAILABLE or not texts:
        return None
    return [vec.tolist() for vec in model.embed(texts)]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def similarity(a: str, b: str) -> tuple[float, str]:
    """Semantic similarity in [0, 1], plus which method produced it.

    The method is returned so callers can report honestly which signal a
    verification decision was actually based on.
    """
    vectors = embed([a, b])
    if vectors is not None:
        # bge cosine sits in roughly [0.3, 1.0] for English text; rescale so
        # thresholds mean something closer to intuition.
        raw = cosine(vectors[0], vectors[1])
        return max(0.0, min(1.0, (raw - 0.3) / 0.7)), "embedding"

    from rapidfuzz import fuzz

    return fuzz.token_set_ratio(a.lower(), b.lower()) / 100.0, "lexical"
