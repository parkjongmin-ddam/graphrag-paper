"""
GraphRAG-Paper - A-M4 - search/engine.py
--------------------------------------------------
Global search (single-call over community summaries) and local search
(seed entity name match -> 1-hop subgraph -> corpus excerpts -> LLM).

This is the Phase A baseline: simple, deterministic, one LLM call per query.
Phase B (agentic) replaces the router and adds grading + self-reflection.
"""

from __future__ import annotations

import logging

from core.artifacts import read_json
from core.config import PipelineConfig
from core.schemas import SearchMode, SearchResult
from core.stage import Stage, StageReport

# ----------------------------- constants -----------------------------
MODEL = "claude-haiku-4-5-20251001"
ANSWER_MAX_TOKENS = 800

# Local search: how aggressively to widen / how much corpus text to attach.
LOCAL_MAX_SEEDS = 8
LOCAL_MAX_PAPERS = 5
LOCAL_PAPER_TEXT_CHARS = 800

GLOBAL_PROMPT = """You answer questions about retrieval-augmented generation (RAG) research using community summaries built from a knowledge graph over RAG papers.

Use ONLY the provided summaries. If they don't address the question, say so honestly.
Keep the answer focused (2-4 short paragraphs). Cite specific methods/models/datasets by name when relevant."""

LOCAL_PROMPT = """You answer questions about RAG research using a focused subgraph of related entities plus excerpts from the source papers.

Use ONLY the provided context. Be concrete: cite specific methods, models, and datasets by name. Avoid generic statements. If the context is insufficient, say so."""

log = logging.getLogger("search")


# ----------------------------- LLM -----------------------------
def _llm_answer(query: str, context: str, system_prompt: str) -> str:
    import anthropic  # lazy

    client = anthropic.Anthropic()  # ANTHROPIC_API_KEY from env
    resp = client.messages.create(
        model=MODEL,
        max_tokens=ANSWER_MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": f"Question: {query}\n\nContext:\n{context}"}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


# ----------------------------- global -----------------------------
def _global_search(query: str, kg: dict) -> SearchResult:
    summarized = [c for c in kg.get("communities") or [] if (c.get("title") or "").strip()]
    if not summarized:
        return SearchResult(
            query=query, mode="global",
            answer="(no summarized communities yet — run the communities stage with --allow-network first)",
        )
    blocks = [f"## {c['title']}\n{c.get('summary') or ''}" for c in summarized]
    context = "\n\n".join(blocks)
    answer = _llm_answer(query, context, GLOBAL_PROMPT)
    return SearchResult(
        query=query, mode="global", answer=answer,
        contexts=tuple(c.get("summary") or "" for c in summarized),
        sources=(),
    )


# ----------------------------- local -----------------------------
def _find_seeds(query: str, entities: list[dict], k: int = LOCAL_MAX_SEEDS) -> list[dict]:
    """Entities whose name (>=4 chars) appears as a substring of the query (case-insensitive)."""
    q = query.lower()
    out: list[dict] = []
    seen_ids: set[str] = set()
    for e in entities:
        name = (e.get("name") or "").lower().strip()
        if len(name) < 4 or e["id"] in seen_ids:
            continue
        if name in q:
            seen_ids.add(e["id"])
            out.append(e)
            if len(out) >= k:
                break
    return out


def _local_search(query: str, kg: dict, config: PipelineConfig) -> SearchResult:
    entities = kg.get("entities") or []
    relations = kg.get("relations") or []
    ent_by_id = {e["id"]: e for e in entities}

    seeds = _find_seeds(query, entities)
    if not seeds:
        return SearchResult(
            query=query, mode="local",
            answer="(no entities in the query matched any name in the graph)",
        )

    # 1-hop expansion over relations
    seed_ids = {s["id"] for s in seeds}
    neighborhood: set[str] = set(seed_ids)
    for r in relations:
        if r.get("source_id") in seed_ids:
            neighborhood.add(r["target_id"])
        if r.get("target_id") in seed_ids:
            neighborhood.add(r["source_id"])

    # entity descriptions (skip Papers — they go into the paper-block section instead)
    entity_lines: list[str] = []
    paper_ids: list[str] = []
    for eid in neighborhood:
        e = ent_by_id.get(eid)
        if not e:
            continue
        if e["type"] == "Paper":
            paper_ids.append(eid)
            continue
        desc = (e.get("description") or "").strip()
        entity_lines.append(f"- [{e['type']}] {e['name']}" + (f": {desc}" if desc else ""))

    # also gather source_papers from non-Paper entities
    for eid in neighborhood:
        e = ent_by_id.get(eid)
        if e:
            for pid in (e.get("source_papers") or []):
                if pid not in paper_ids:
                    paper_ids.append(pid)
            if len(paper_ids) >= LOCAL_MAX_PAPERS * 3:
                break

    # attach a few corpus paper excerpts
    paper_blocks: list[str] = []
    used_sources: list[str] = []
    for pid in paper_ids[: LOCAL_MAX_PAPERS * 3]:
        path = config.corpus_dir / f"{pid}.json"
        if not path.exists():
            continue
        doc = read_json(path)
        text = doc.get("abstract") or doc.get("intro") or ""
        if not text:
            continue
        paper_blocks.append(f"## {doc.get('title') or pid}\n{text[:LOCAL_PAPER_TEXT_CHARS]}")
        used_sources.append(pid)
        if len(paper_blocks) >= LOCAL_MAX_PAPERS:
            break

    context = "\n\n".join(
        block for block in ["Entities:\n" + "\n".join(entity_lines), *paper_blocks]
        if block.strip()
    )
    answer = _llm_answer(query, context, LOCAL_PROMPT)
    return SearchResult(
        query=query, mode="local", answer=answer,
        contexts=(context,),
        sources=tuple(used_sources),
    )


# ----------------------------- entry point -----------------------------
def search(query: str, config: PipelineConfig, mode: SearchMode = "global") -> SearchResult:
    """Answer `query` against the knowledge graph in the chosen mode."""
    kg = read_json(config.knowledge_graph_path)
    if mode == "global":
        return _global_search(query, kg)
    if mode == "local":
        return _local_search(query, kg, config)
    raise ValueError(f"unknown search mode: {mode!r}")


class SearchStage(Stage):
    """Smoke-test wiring with a probe query in global mode."""

    name = "search"
    milestone = "A-M4"
    requires = ("communities",)
    PROBE_QUERY = "What methods improve retrieval-augmented generation?"

    def run(self, config: PipelineConfig) -> StageReport:
        if not config.knowledge_graph_path.exists():
            return self.skipped("no knowledge_graph.json (build the graph first)")
        if not config.allow_network:
            return self.skipped(
                "network gated; pass --allow-network or set GRAPHRAG_ALLOW_NETWORK=1"
            )
        result = search(self.PROBE_QUERY, config)
        return self.ok(
            answer_len=len(result.answer),
            contexts=len(result.contexts),
            sources=len(result.sources),
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from core.pipeline import PipelineRunner
    PipelineRunner([SearchStage()]).run(PipelineConfig.from_env())


if __name__ == "__main__":
    main()
