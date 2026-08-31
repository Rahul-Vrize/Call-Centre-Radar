"""Cross-call intelligence: which issues recur.

Embeds each call's intent + summary and clusters them with HDBSCAN. No
predefined taxonomy, so themes emerge from the data rather than from a category
list someone guessed at in advance — which is the only way "trending" means
anything.

Uses `sklearn.cluster.HDBSCAN` (shipped since scikit-learn 1.3) rather than the
standalone `hdbscan` package, which needs a C compiler and routinely fails to
build on Windows.

Cluster names come from c-TF-IDF: terms that are frequent *inside* a cluster and
rare outside it. Deterministic and free, where an LLM naming pass costs a
request per cluster and renames things between runs.

Also backs repeat-contact detection: same customer + same cluster + within N
days, which feeds the attention score.
"""
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass

from app.pipeline import embeddings

#: Absolute floor for what counts as a cluster rather than noise.
MIN_CLUSTER_SIZE = 5

#: Cluster size scales with the corpus. A fixed floor of 5 is right for a
#: 100-call sample and badly wrong for 1,441: it produced 74 clusters, 38 of
#: them under ten calls, which is a fragment list rather than a trends view.
#: ~1.5% of the corpus keeps the count in the readable 10-25 range at any size.
MIN_CLUSTER_FRACTION = 0.015

#: Two clusters whose centroids are this similar are the same issue said two
#: ways. HDBSCAN split "reset / password / link" into two separate clusters on
#: the full corpus; merging by centroid catches that without hand-tuning.
MERGE_SIMILARITY = 0.90

#: Words too generic to name a banking-support cluster.
STOPWORDS = {
    "a", "about", "account", "agent", "an", "and", "are", "as", "asked",
    "asks", "at", "bank", "be", "been", "but", "by", "call", "caller",
    "completed", "confirmed", "customer", "customer's", "ended", "entered",
    "for", "from", "gathered", "gave", "had", "has", "have", "he", "her",
    "his", "i", "in", "intent", "is", "issue", "it", "no", "not", "of",
    "on", "or", "outcome", "promised", "provided", "request", "requested",
    "resolved", "s", "she", "status", "t", "that", "the", "their", "them",
    "they", "this", "to", "unresolved", "wanted", "wants", "was", "we",
    "were", "with", "you", "your"
}


@dataclass
class ClusterResult:
    labels: list[int]              # cluster id per input, -1 = noise
    names: dict[int, str]          # cluster id -> human-readable name
    noise_ratio: float


def _tokens(text: str) -> list[str]:
    return [
        w for w in re.findall(r"[a-z]+", text.lower())
        if len(w) > 2 and w not in STOPWORDS
    ]


def name_clusters(texts: list[str], labels: list[int]) -> dict[int, str]:
    """Name each cluster by terms common *within* it and rare outside it.

    Scored on document frequency, not raw term frequency. That distinction
    matters: with raw counts, a word repeated three times in one summary
    outranks a word appearing once in twenty-five summaries, so a coherent
    cluster of 28 `pay_bill` calls ended up labelled "outcome / intent /
    entered" — rare words that happened to repeat — while "pay" and "bill",
    present in nearly every document, were pushed down by their corpus
    frequency.

    Using within-cluster document frequency (what share of this cluster's calls
    mention the term) times a damped inverse document frequency picks terms that
    actually characterise the group.
    """
    global_docs = Counter()          # docs in the corpus containing a term
    cluster_docs: dict[int, Counter] = {}   # docs in a cluster containing a term
    cluster_sizes = Counter()

    for text, label in zip(texts, labels):
        terms = set(_tokens(text))
        global_docs.update(terms)
        if label != -1:
            cluster_docs.setdefault(label, Counter()).update(terms)
            cluster_sizes[label] += 1

    n_docs = max(len(texts), 1)
    names: dict[int, str] = {}

    for label, docs in cluster_docs.items():
        size = max(cluster_sizes[label], 1)
        scored = {
            # share of the cluster mentioning it  x  how rare it is corpus-wide
            term: (n / size) * math.log(n_docs / (1 + global_docs[term]))
            for term, n in docs.items()
            # A term in under a third of the cluster doesn't characterise it.
            if n / size >= 0.33
        }
        top = sorted(scored, key=scored.get, reverse=True)[:3]
        if not top:  # nothing shared widely enough — fall back to plain frequency
            top = [t for t, _ in docs.most_common(3)]
        names[label] = " / ".join(top) if top else f"cluster {label}"

    return names


def name_cluster_readable(terms: str, samples: list[str]) -> str:
    """Turn c-TF-IDF terms into something a manager would say out loud.

    The terms are the honest, deterministic output — they prove no taxonomy was
    supplied, because they are literally the words that distinguish this group
    from the rest of the corpus. But "gas / fossil / pay" is not a sentence a
    support manager would ever utter, and "fossil" is half a utility company's
    name that happened to be discriminative.

    So: keep the terms as the evidence, and add a readable name beside them.
    One LLM call per cluster — ten calls for the whole corpus — and it names
    the group from examples rather than inventing a category first, so the
    clustering is still what decided the grouping.

    Falls back to the terms themselves if the model is unavailable: a slightly
    ugly name is better than a missing one.
    """
    from app.pipeline import reasoning

    prompt = (
        "Name this group of customer support calls in 2-4 plain words a support "
        "manager would use. No jargon, no punctuation, no quotes.\n\n"
        f"Distinguishing terms: {terms}\n\nExample calls:\n"
        + "\n".join(f"- {s[:130]}" for s in samples[:6])
        + "\n\nReply with the name only."
    )
    try:
        # 300, not 30. The name itself is three words, but reasoning models
        # (gpt-oss on Bedrock among them) spend the budget thinking BEFORE
        # emitting an answer — at 24 tokens the reasoning consumed all of it
        # and the text block came back empty, so every cluster silently fell
        # back to its raw terms.
        name = reasoning.complete_text(prompt, max_tokens=300).strip()
    except Exception:
        return terms

    name = name.strip().strip('".').replace("\n", " ")
    if not name or len(name) > 42:
        return terms
    return name[0].upper() + name[1:]


def _merge_similar(matrix, labels: list[int], threshold: float) -> list[int]:
    """Merge clusters whose centroids are near-identical.

    HDBSCAN optimises local density, so a single topic phrased two ways can
    land in two clusters. Comparing centroids afterwards is a cheap, principled
    fix — no re-clustering, no magic per-topic rules.
    """
    import numpy as np

    ids = sorted({label for label in labels if label != -1})
    if len(ids) < 2:
        return labels

    centroids = {}
    for cid in ids:
        rows = matrix[[i for i, label in enumerate(labels) if label == cid]]
        centre = rows.mean(axis=0)
        norm = np.linalg.norm(centre)
        centroids[cid] = centre / norm if norm else centre

    # Union-find so a chain of similar clusters collapses to one representative.
    parent = {cid: cid for cid in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if float(centroids[a] @ centroids[b]) >= threshold:
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[max(ra, rb)] = min(ra, rb)

    return [find(label) if label != -1 else -1 for label in labels]


def cluster_calls(
    texts: list[str],
    min_cluster_size: int | None = None,
    merge_threshold: float = MERGE_SIMILARITY,
) -> ClusterResult:
    """Embed and cluster. Returns all -1 (noise) if clustering isn't possible,
    so callers get a well-formed empty result rather than an exception."""
    if min_cluster_size is None:
        min_cluster_size = max(
            MIN_CLUSTER_SIZE, round(len(texts) * MIN_CLUSTER_FRACTION)
        )
    if len(texts) < min_cluster_size:
        return ClusterResult(labels=[-1] * len(texts), names={}, noise_ratio=1.0)

    vectors = embeddings.embed(texts)
    if vectors is None:
        return ClusterResult(labels=[-1] * len(texts), names={}, noise_ratio=1.0)

    try:
        import numpy as np
        from sklearn.cluster import HDBSCAN
    except ImportError:
        return ClusterResult(labels=[-1] * len(texts), names={}, noise_ratio=1.0)

    matrix = np.array(vectors, dtype=float)
    # Cosine geometry via L2 normalisation + euclidean — HDBSCAN's metric
    # options don't include cosine, and normalised euclidean is equivalent.
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix = matrix / np.clip(norms, 1e-9, None)

    labels = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=1,
        metric="euclidean",
    ).fit_predict(matrix).tolist()

    labels = _merge_similar(matrix, labels, merge_threshold)

    noise = sum(1 for label in labels if label == -1)
    return ClusterResult(
        labels=labels,
        names=name_clusters(texts, labels),
        noise_ratio=noise / len(labels),
    )
