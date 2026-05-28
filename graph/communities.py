"""
GraphRAG-Paper - A-M2/M3 - graph/communities.py
--------------------------------------------------
Leiden community detection over the knowledge graph (A-M2), then an LLM summary
per community (A-M3). Communities are merged back into knowledge_graph.json.
"""

from __future__ import annotations

import json
import logging
import re
import time

from core.artifacts import read_json, write_json
from core.config import PipelineConfig
from core.schemas import Community
from core.stage import Stage, StageReport

# ----------------------------- constants -----------------------------
MODEL = "claude-haiku-4-5-20251001"  # summary LLM (same as A-M1)
MIN_COMMUNITY_SIZE = 5  # only summarize communities of this size or larger
SUMMARY_MAX_TOKENS = 600
SLEEP_SEC = 0.3

SUMMARY_SYSTEM_PROMPT = """Given a list of entities forming a community within a corpus of retrieval-augmented generation (RAG) research papers, produce:
- a short TITLE (max 8 words) capturing the community's theme
- a 2-3 sentence SUMMARY describing what unites these entities

Return ONLY a JSON object, no prose, no markdown fences:
{"title": "...", "summary": "..."}"""

log = logging.getLogger("communities")


LEIDEN_SEED = 42  # deterministic partition across runs


def detect_communities(config: PipelineConfig) -> list[Community]:
    """Flat Leiden community detection on the knowledge graph.

    Treats relations as undirected, edge weight 1. Singleton nodes (no relations)
    appear as size-1 communities. Hierarchical levels (>0) and per-community
    summaries are filled in by A-M3.
    """
    import igraph as ig
    import leidenalg

    kg = read_json(config.knowledge_graph_path)
    entities = kg.get("entities", [])
    relations = kg.get("relations", [])
    ent_ids = [e["id"] for e in entities]
    idx = {eid: i for i, eid in enumerate(ent_ids)}

    edges: list[tuple[int, int]] = []
    for r in relations:
        s, t = r.get("source_id"), r.get("target_id")
        if s in idx and t in idx and s != t:
            edges.append((idx[s], idx[t]))

    g = ig.Graph(n=len(ent_ids), edges=edges, directed=False)
    partition = leidenalg.find_partition(
        g, leidenalg.ModularityVertexPartition, seed=LEIDEN_SEED
    )

    communities: list[Community] = []
    for ci, members in enumerate(partition):
        if not members:
            continue
        communities.append(Community(
            id=f"c0:{ci}",
            level=0,
            entity_ids=tuple(ent_ids[i] for i in members),
        ))
    log.info(
        "Leiden: %d entities, %d edges -> %d communities (modularity=%.3f)",
        len(ent_ids), len(edges), len(communities), partition.modularity,
    )
    return communities


def _summarize_one(community: Community, entities_by_id: dict[str, dict]) -> tuple[str, str]:
    """Call claude-haiku-4-5 to produce (title, summary) for one community."""
    import anthropic

    lines: list[str] = []
    for eid in community.entity_ids:
        e = entities_by_id.get(eid)
        if not e:
            continue
        desc = (e.get("description") or "").strip()[:120]
        line = f"- [{e['type']}] {e['name']}"
        if desc:
            line += f" — {desc}"
        lines.append(line)
    entity_block = "\n".join(lines)

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=SUMMARY_MAX_TOKENS,
        system=SUMMARY_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Entities:\n\n{entity_block}"}],
    )
    raw = "".join(block.text for block in resp.content if block.type == "text")
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return "", ""
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        log.warning("%s: summary JSON decode failed: %s", community.id, e)
        return "", ""
    return (data.get("title") or "").strip(), (data.get("summary") or "").strip()


def summarize_communities(
    communities: list[Community],
    entities: list[dict],
    min_size: int = MIN_COMMUNITY_SIZE,
) -> list[Community]:
    """LLM-summarize communities with size >= min_size; others returned unchanged."""
    entities_by_id = {e["id"]: e for e in entities}
    targets = sum(1 for c in communities if len(c.entity_ids) >= min_size)
    log.info("summarizing %d communities (size >= %d)", targets, min_size)
    out: list[Community] = []
    seen = 0
    for c in communities:
        if len(c.entity_ids) < min_size:
            out.append(c)
            continue
        seen += 1
        try:
            title, summary = _summarize_one(c, entities_by_id)
        except Exception as e:
            log.exception("%s: summary failed: %s", c.id, e)
            out.append(c)
            continue
        out.append(Community(
            id=c.id, level=c.level, entity_ids=c.entity_ids,
            title=title, summary=summary,
        ))
        log.info("[%d/%d] %s (size=%d): %s", seen, targets, c.id, len(c.entity_ids), title or "(empty)")
        time.sleep(SLEEP_SEC)
    return out


class CommunityStage(Stage):
    name = "communities"
    milestone = "A-M2"
    requires = ("extract_graph",)

    def run(self, config: PipelineConfig) -> StageReport:
        kg_path = config.knowledge_graph_path
        if not kg_path.exists():
            return self.skipped("no knowledge_graph.json (run extract_graph first)")

        kg = read_json(kg_path)
        cached_by_id = {
            c["id"]: c for c in (kg.get("communities") or [])
            if (c.get("title") or "").strip()
        }

        communities = detect_communities(config)

        if config.allow_network:
            if cached_by_id and not config.force:
                communities = [
                    Community(
                        id=c.id, level=c.level, entity_ids=c.entity_ids,
                        title=cached_by_id.get(c.id, {}).get("title", ""),
                        summary=cached_by_id.get(c.id, {}).get("summary", ""),
                    )
                    for c in communities
                ]
                log.info(
                    "reused %d cached summaries (use --force to regenerate)",
                    sum(1 for c in communities if c.title),
                )
            else:
                communities = summarize_communities(communities, kg.get("entities") or [])

        kg["communities"] = [c.__dict__ for c in communities]
        write_json(kg_path, kg)
        return self.ok(
            outputs=(kg_path,),
            communities=len(communities),
            summarized=sum(1 for c in communities if c.title),
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from core.pipeline import PipelineRunner
    PipelineRunner([CommunityStage()]).run(PipelineConfig.from_env())


if __name__ == "__main__":
    main()
