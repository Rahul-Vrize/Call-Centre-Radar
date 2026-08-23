"""Grounded reasoning layer: intent, resolution, and the <=40-word summary, via
a locally-served open LLM (Ollama) forced into a strict JSON schema where every
judgment carries a nested evidence object. See RADAR_PLAYBOOK.md, Stage 3, for
the full schema example."""
from dataclasses import dataclass

from app.config import settings


@dataclass
class RawEvidence:
    turn_id: int
    timestamp: str
    quote: str


@dataclass
class ReasoningResult:
    intent_label: str
    intent_evidence: RawEvidence
    resolution_status: str  # "resolved" | "unresolved" | "partial"
    resolution_evidence: RawEvidence
    summary: str  # <= 40 words, validated before returning


def analyze_call(transcript_text: str) -> ReasoningResult:
    """Call the local LLM (settings.ollama_model) with a schema-constrained
    prompt; parse and validate the JSON response; enforce the 40-word summary
    cap. Does NOT run the evidence verifier itself — that happens once, in
    verifier.py, on every evidence object regardless of which stage produced it.
    """
    raise NotImplementedError
