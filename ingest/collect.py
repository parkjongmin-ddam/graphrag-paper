"""
GraphRAG-Paper - A-M0 - collect.py
--------------------------------------------------
Seed papers -> forward citations -> scoring -> top-N selection.

- Source: Semantic Scholar Graph API (free; API key optional)
- Only papers with an arXiv ID are kept (so LaTeX-first section extraction works)
- Output: data/paper_list.json (input to the next stage, extract_sections.py)

Standalone:
    pip install requests
    set S2_API_KEY=...                 # optional; lower rate limit without it
    set GRAPHRAG_ALLOW_NETWORK=1       # required to make live calls
    python ingest/collect.py
"""

from __future__ import annotations

import logging
import math
import os
import time

from core.artifacts import write_records
from core.config import PipelineConfig
from core.schemas import PaperRef
from core.stage import Stage, StageReport

# ----------------------------- constants -----------------------------
S2_BASE = "https://api.semanticscholar.org/graph/v1"

# RAG lineage seeds. "arXiv:<id>" form is resolved natively by Semantic Scholar.
SEED_PAPERS: tuple[str, ...] = (
    "arXiv:2005.11401",  # Lewis et al. 2020 - original RAG
    "arXiv:2007.01282",  # Fusion-in-Decoder
)

# Corpus cohesion keywords (title/abstract match score).
RAG_KEYWORDS = [
    "retrieval-augmented", "retrieval augmented", "rag",
    "retriever", "retrieval", "dense passage", "reranking", "rerank",
    "open-domain question answering", "knowledge-intensive",
    "passage retrieval", "fusion-in-decoder", "self-rag", "corrective",
    "hallucination", "grounding", "vector", "embedding",
]

REQUEST_FIELDS = "paperId,title,abstract,year,citationCount,externalIds,fieldsOfStudy"
SLEEP_SEC = 1.1  # spacing between calls to ease rate limits

TARGET_N = 100     # expanded from validated 50 (50-paper snapshot kept as *_50p)
MIN_YEAR = 2019    # drop papers older than this

# Score weights.
W_KEYWORD = 1.0
W_CITATION = 0.6
W_RECENCY = 0.4

log = logging.getLogger("collect")


# --------------------------- API helpers ---------------------------
def s2_get(path: str, params: dict, max_retry: int = 5) -> dict:
    """Semantic Scholar GET with exponential backoff on 429/5xx."""
    import requests  # lazy: keep the harness importable without requests installed

    api_key = os.environ.get("S2_API_KEY")
    headers = {"x-api-key": api_key} if api_key else {}
    url = f"{S2_BASE}{path}"
    for attempt in range(max_retry):
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (429, 500, 502, 503):
            wait = SLEEP_SEC * (2 ** attempt)
            log.warning("status=%s, retrying in %.1fs (%d/%d)",
                        resp.status_code, wait, attempt + 1, max_retry)
            time.sleep(wait)
            continue
        resp.raise_for_status()
    raise RuntimeError(f"S2 request failed: {url} params={params}")


def get_references(paper_id: str, max_results: int = 1000) -> list[str]:
    """Collect outbound references (papers cited BY paper_id), returning paperIds.

    Used to populate PaperRef.references so build_corpus can hand CITES edges
    to A-M1 entity extraction.
    """
    results: list[str] = []
    offset, limit = 0, 1000
    while len(results) < max_results:
        data = s2_get(
            f"/paper/{paper_id}/references",
            {"fields": "paperId", "limit": limit, "offset": offset},
        )
        batch = data.get("data", [])
        for item in batch:
            cited = item.get("citedPaper") or {}
            pid = cited.get("paperId")
            if pid:
                results.append(pid)
        if data.get("next") is None or not batch:
            break
        offset = data["next"]
        time.sleep(SLEEP_SEC)
    return results[:max_results]


def get_citing_papers(paper_id: str, max_results: int = 5000) -> list[dict]:
    """Collect forward citations (papers citing paper_id) with pagination.

    Caps at max_results: S2's /citations endpoint rejects offsets past ~9000
    with HTTP 400, and top-N selection downstream needs only a fraction of this.
    """
    results: list[dict] = []
    offset, limit = 0, 1000
    while len(results) < max_results:
        data = s2_get(
            f"/paper/{paper_id}/citations",
            {"fields": REQUEST_FIELDS, "limit": limit, "offset": offset},
        )
        batch = data.get("data", [])
        results.extend(c["citingPaper"] for c in batch if c.get("citingPaper"))
        if data.get("next") is None or not batch:
            break
        offset = data["next"]
        time.sleep(SLEEP_SEC)
    log.info("%s -> %d citing papers", paper_id, len(results))
    return results[:max_results]


# --------------------------- scoring ---------------------------
def keyword_score(paper: dict) -> float:
    text = f"{paper.get('title') or ''} {paper.get('abstract') or ''}".lower()
    hits = sum(1 for kw in RAG_KEYWORDS if kw in text)
    return hits / len(RAG_KEYWORDS)


def citation_score(paper: dict, max_log: float) -> float:
    c = paper.get("citationCount") or 0
    return math.log1p(c) / max_log if max_log else 0.0


def recency_score(paper: dict, min_year: int, max_year: int) -> float:
    y = paper.get("year") or min_year
    span = max(max_year - min_year, 1)
    return (y - min_year) / span


def arxiv_id_of(paper: dict) -> str | None:
    ext = paper.get("externalIds") or {}
    return ext.get("ArXiv")


# ----------------------------- core -----------------------------
def collect(config: PipelineConfig) -> list[PaperRef]:
    """Run the full collect pipeline and persist data/paper_list.json.

    Makes live Semantic Scholar calls. Callers (e.g. CollectStage) are
    responsible for gating network access.
    """
    # 1) forward citations per seed, de-duplicated
    candidates: dict[str, dict] = {}
    for seed in SEED_PAPERS:
        for p in get_citing_papers(seed):
            pid = p.get("paperId")
            if pid and pid not in candidates:
                candidates[pid] = p
        time.sleep(SLEEP_SEC)
    log.info("%d candidates after de-dup", len(candidates))

    # 2) filter: arXiv ID present + year + abstract present
    pool = [
        p for p in candidates.values()
        if arxiv_id_of(p) and (p.get("year") or 0) >= MIN_YEAR and p.get("abstract")
    ]
    log.info("%d after arxiv/year/abstract filter", len(pool))
    if not pool:
        log.warning("no candidates; adjust seeds/keywords/min_year")
        return []

    # 3) score (keyword + citations + recency)
    max_log = max((math.log1p(p.get("citationCount") or 0) for p in pool), default=1.0)
    years = [p.get("year") for p in pool if p.get("year")]
    min_y, max_y = (min(years), max(years)) if years else (MIN_YEAR, MIN_YEAR)
    for p in pool:
        p["_score"] = (
            W_KEYWORD * keyword_score(p)
            + W_CITATION * citation_score(p, max_log)
            + W_RECENCY * recency_score(p, min_y, max_y)
        )

    # 4) top-N
    pool.sort(key=lambda p: p["_score"], reverse=True)
    selected = pool[: TARGET_N]

    # 4.5) fetch outbound references per selected paper (for CITES relations in A-M1)
    for i, p in enumerate(selected, 1):
        p["_references"] = get_references(p["paperId"])
        log.info("[%d/%d] %s -> %d references", i, len(selected), p["paperId"], len(p["_references"]))
        time.sleep(SLEEP_SEC)

    # 5) to typed refs + persist
    refs = [
        PaperRef(
            paper_id=p["paperId"],
            arxiv_id=arxiv_id_of(p),
            title=p.get("title"),
            abstract=p.get("abstract"),
            year=p.get("year"),
            citation_count=p.get("citationCount"),
            score=round(p["_score"], 4),
            fields=tuple(p.get("fieldsOfStudy") or ()),
            references=tuple(p["_references"]),
        )
        for p in selected
    ]
    write_records(config.paper_list_path, refs)
    log.info("saved %d papers -> %s", len(refs), config.paper_list_path)
    for r in refs[:10]:
        log.info("  [%.3f] (%s) %s", r.score or 0.0, r.year, (r.title or "")[:80])
    return refs


class CollectStage(Stage):
    """A-M0: build paper_list.json from seed forward-citations."""

    name = "collect"
    milestone = "A-M0"

    def run(self, config: PipelineConfig) -> StageReport:
        out = config.paper_list_path
        if out.exists() and not config.force:
            return self.skipped(f"{out.name} exists (use force to rebuild)")
        if not config.allow_network:
            return self.skipped(
                "network gated; pass --allow-network or set GRAPHRAG_ALLOW_NETWORK=1"
            )
        refs = collect(config)
        if not refs:
            return self.failed("collect produced 0 papers; check seeds/filters")
        return self.ok(outputs=(out,), papers=len(refs))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from core.pipeline import PipelineRunner
    PipelineRunner([CollectStage()]).run(PipelineConfig.from_env())


if __name__ == "__main__":
    main()
