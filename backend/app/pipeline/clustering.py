"""Cross-call trending: embed each call's summary/intent, cluster with HDBSCAN
(no predefined issue taxonomy), and bucket cluster frequency by day. Also
backs repeat-contact detection: same customer, same cluster, within N days."""
from dataclasses import dataclass


@dataclass
class ClusterAssignment:
    call_id: str
    cluster_id: int


def embed_summaries(summaries: list[str]) -> list[list[float]]:
    """sentence-transformers (all-MiniLM) embeddings, local, no API calls."""
    raise NotImplementedError


def cluster_calls(embeddings: list[list[float]]) -> list[int]:
    """HDBSCAN over the embedding space -> cluster id per call (-1 = noise)."""
    raise NotImplementedError


def label_cluster(sample_summaries: list[str]) -> str:
    """One short LLM call to name a cluster from a handful of its summaries."""
    raise NotImplementedError
