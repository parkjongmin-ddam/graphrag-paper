"""
GraphRAG-Paper - B-M6 - search/rerank.py
--------------------------------------------------
Cross-encoder re-ranking layered on top of dense (bi-encoder) vector retrieval.

The dense retriever (search/vector.py) fetches a pool of candidates; this module
re-scores each candidate (query, passage) pair with a cross-encoder so the model
actually attends to both texts jointly, then we keep the top-k by reranker score.
This is the standard retrieve+rerank pattern and typically lifts precision on
fact-specific questions where the bi-encoder alone confuses thematically-related
passages with the one that actually contains the answer.

Model: Xenova/ms-marco-MiniLM-L-12-v2 (~120MB, fastembed local — no API cost).
Loaded lazily and cached so the weight download happens once per process.

Failure policy: any error inside the reranker (model load, scoring) falls back
to the input order truncated to top_k, logged honestly. The agent thus stays
functional even if the reranker is unavailable.
"""

from __future__ import annotations

import functools
import logging

RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-12-v2"

log = logging.getLogger("rerank")


@functools.lru_cache(maxsize=1)
def _get_reranker():
    """Lazy-load and process-cache the cross-encoder (one weight download)."""
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    return TextCrossEncoder(model_name=RERANK_MODEL)


def rerank_hits(query: str, hits: list[dict], top_k: int) -> list[dict]:
    """Re-score `hits` by (query, hit['text']) cross-encoder and return top_k.

    Hits keep all their original metadata (paper_id, title, section, chunk_idx);
    only the order — and the count — changes. On any failure the function falls
    back to `hits[:top_k]` (input order) rather than raising, so a transient
    model issue does not break a live query path.
    """
    if not hits or top_k <= 0:
        return []
    try:
        ranker = _get_reranker()
        texts = [h.get("text", "") for h in hits]
        scores = list(ranker.rerank(query, texts))
        scored = sorted(zip(scores, hits), key=lambda s: s[0], reverse=True)
        log.info(
            "rerank: %d -> %d (top score=%.3f, bottom kept=%.3f)",
            len(hits), min(top_k, len(scored)),
            scored[0][0] if scored else 0.0,
            scored[min(top_k, len(scored)) - 1][0] if scored else 0.0,
        )
        return [h for _, h in scored[:top_k]]
    except Exception as e:  # noqa: BLE001 — degrade gracefully on any reranker error
        log.exception("rerank failed (%s); falling back to input order", e)
        return hits[:top_k]


__all__ = ["rerank_hits", "RERANK_MODEL"]
