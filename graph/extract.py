"""
GraphRAG-Paper - A-M1 - graph/extract.py
--------------------------------------------------
LLM entity + relation extraction across corpus documents. Each corpus paper
also becomes a Paper entity (deterministic), and CITES relations are added
from corpus.citations against papers in our own corpus (deterministic).

Output: data/graph/knowledge_graph.json (entities + relations; communities empty)
"""

from __future__ import annotations

import json
import logging
import re
import time

from core.artifacts import read_json, write_json
from core.config import PipelineConfig
from core.schemas import Entity, KnowledgeGraph, Relation
from core.stage import Stage, StageReport

# ----------------------------- constants -----------------------------
MODEL = "claude-haiku-4-5-20251001"
# 8000 not 2000: full-text (intro+related) papers produce long entity/relation
# JSON that truncated at 2000 tokens mid-array, failing the JSON parse and
# dropping the whole paper's contribution. ~4x headroom over observed ~2000-token
# outputs. (claude-haiku-4-5 supports well beyond this.)
MAX_TOKENS = 8000
SLEEP_SEC = 0.3

# Paper entities are auto-created from corpus docs; LLM extracts the other 7 types.
_LLM_ENTITY_TYPES = {"Method", "Model", "Dataset", "Metric", "Task", "Author", "Institution"}
# CITES is deterministic from corpus.citations; LLM extracts the other 6 relation types.
_LLM_RELATION_TYPES = {"USES", "EVALUATED_ON", "IMPROVES", "OUTPERFORMS", "COMBINES", "PROPOSED_BY"}

SYSTEM_PROMPT = """You extract structured knowledge from research papers on retrieval-augmented generation (RAG).

Extract ONLY entities and relations matching these schemas.

ENTITY TYPES (with examples):
- Method: techniques/algorithms — "Dense Passage Retrieval", "REALM", "Fusion-in-Decoder"
- Model: pre-trained or proposed models — "BERT", "T5", "GPT-3", "Llama-2"
- Dataset: evaluation/training datasets — "Natural Questions", "TriviaQA", "MS MARCO"
- Metric: evaluation measures — "Exact Match", "F1", "BLEU"
- Task: NLP tasks — "Open-domain QA", "Fact Checking", "Summarization"
- Author: when named in text — "Lewis et al.", "Karpukhin et al."
- Institution: labs/companies — "Facebook AI", "Google Research", "OpenAI"

RELATION TYPES (source -> target):
- USES: a Method/Model uses another component
- EVALUATED_ON: a Method/Model evaluated on a Dataset/Task
- IMPROVES: incremental improvement over a baseline
- OUTPERFORMS: beats a baseline (often with a Metric)
- COMBINES: hybrid combining multiple components
- PROPOSED_BY: a Method/Model proposed by an Author/Institution

Rules:
- Use entity NAMES that literally appear in the text (so source/target in relations match).
- Skip generic words ("the model", "our approach").
- Keep descriptions short (one phrase).
- Return ONLY a JSON object. No prose, no markdown fences.

Format:
{"entities": [{"name": "...", "type": "Method", "description": "..."}, ...],
 "relations": [{"source": "...", "target": "...", "type": "USES", "description": "..."}, ...]}"""

log = logging.getLogger("extract_graph")


# ----------------------------- LLM -----------------------------
def _call_llm(text: str) -> str:
    """Call claude-haiku-4-5 with the extraction prompt; return raw text content."""
    import anthropic  # lazy: keep the harness importable without the SDK

    client = anthropic.Anthropic()  # ANTHROPIC_API_KEY from env
    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Paper text:\n\n{text}"}],
    )
    return "".join(block.text for block in resp.content if block.type == "text")


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_llm(raw: str) -> tuple[list[dict], list[dict]]:
    """Pull entities/relations lists out of the model's JSON response."""
    m = _JSON_RE.search(raw)
    if not m:
        return [], []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        log.warning("JSON decode failed: %s", e)
        return [], []
    return data.get("entities") or [], data.get("relations") or []


# ----------------------------- registry helpers -----------------------------
def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip()


def _ent_id(ent_type: str, name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return f"{ent_type}:{slug}"


def _add_entity(reg: dict[str, Entity], raw_ent: dict, paper_id: str) -> str | None:
    name = _norm(raw_ent.get("name") or "")
    ent_type = raw_ent.get("type")
    if not name or ent_type not in _LLM_ENTITY_TYPES:
        return None
    eid = _ent_id(ent_type, name)
    existing = reg.get(eid)
    if existing is None:
        reg[eid] = Entity(
            id=eid,
            name=name,
            type=ent_type,
            description=(raw_ent.get("description") or "").strip(),
            source_papers=(paper_id,),
        )
    elif paper_id not in existing.source_papers:
        reg[eid] = Entity(
            id=existing.id,
            name=existing.name,
            type=existing.type,
            description=existing.description,
            source_papers=tuple(list(existing.source_papers) + [paper_id]),
        )
    return eid


def _add_relation(
    out: list[Relation], raw_rel: dict, name_to_id: dict[str, str], paper_id: str
) -> None:
    rtype = raw_rel.get("type")
    if rtype not in _LLM_RELATION_TYPES:
        return
    src = _norm(raw_rel.get("source") or "").lower()
    tgt = _norm(raw_rel.get("target") or "").lower()
    sid = name_to_id.get(src)
    tid = name_to_id.get(tgt)
    if not sid or not tid:
        return  # endpoint not in extracted entities for this paper
    out.append(Relation(
        source_id=sid,
        target_id=tid,
        type=rtype,
        description=(raw_rel.get("description") or "").strip(),
        source_papers=(paper_id,),
    ))


# ----------------------------- core -----------------------------
def extract_graph(config: PipelineConfig) -> KnowledgeGraph:
    """LLM-extract entities + relations from each corpus doc; merge to a KG.

    Also: (a) every corpus doc becomes a Paper entity, (b) CITES relations are
    added deterministically from corpus.citations against our own corpus.
    """
    corpus_files = sorted(config.corpus_dir.glob("*.json"))
    docs = [read_json(f) for f in corpus_files]
    log.info("loaded %d corpus docs", len(docs))

    registry: dict[str, Entity] = {}
    relations: list[Relation] = []

    # Paper entities (deterministic)
    for doc in docs:
        pid = doc["paper_id"]
        registry[pid] = Entity(
            id=pid,
            name=doc.get("title") or pid,
            type="Paper",
            description=(doc.get("abstract") or "")[:300],
            source_papers=(pid,),
        )

    # LLM extraction per paper
    for i, doc in enumerate(docs, 1):
        pid = doc["paper_id"]
        text = "\n\n".join(
            s for s in (doc.get("abstract"), doc.get("intro"), doc.get("related_work")) if s
        ).strip()
        if not text:
            log.info("[%d/%d] %s: no text, skipping LLM", i, len(docs), pid)
            continue
        try:
            raw = _call_llm(text)
        except Exception as e:
            log.exception("[%d/%d] %s: LLM call failed: %s", i, len(docs), pid, e)
            continue
        ents, rels = _parse_llm(raw)

        name_to_id: dict[str, str] = {}
        for raw_ent in ents:
            eid = _add_entity(registry, raw_ent, pid)
            if eid:
                name_to_id[_norm(raw_ent["name"]).lower()] = eid
        for raw_rel in rels:
            _add_relation(relations, raw_rel, name_to_id, pid)
        log.info(
            "[%d/%d] %s: ents+=%d rels+=%d (totals ent=%d rel=%d)",
            i, len(docs), pid, len(ents), len(rels), len(registry), len(relations),
        )
        time.sleep(SLEEP_SEC)

    # Deterministic CITES (Paper -> Paper, within our corpus only)
    own_ids = {d["paper_id"] for d in docs}
    cites = 0
    for doc in docs:
        src = doc["paper_id"]
        for tgt in doc.get("citations") or []:
            if tgt in own_ids and tgt != src:
                relations.append(Relation(
                    source_id=src,
                    target_id=tgt,
                    type="CITES",
                    source_papers=(src,),
                ))
                cites += 1
    log.info("added %d CITES relations", cites)

    return KnowledgeGraph(
        entities=tuple(registry.values()),
        relations=tuple(relations),
        communities=(),
    )


class ExtractGraphStage(Stage):
    name = "extract_graph"
    milestone = "A-M1"
    requires = ("build_corpus",)

    def run(self, config: PipelineConfig) -> StageReport:
        corpus_files = sorted(config.corpus_dir.glob("*.json"))
        if not corpus_files:
            return self.skipped("no data/corpus/*.json (run build_corpus first)")
        if config.knowledge_graph_path.exists() and not config.force:
            return self.skipped(
                f"{config.knowledge_graph_path.name} exists (use --force to rebuild)"
            )
        if not config.allow_network:
            return self.skipped(
                "network gated; pass --allow-network or set GRAPHRAG_ALLOW_NETWORK=1"
            )
        kg = extract_graph(config)
        write_json(config.knowledge_graph_path, kg)
        return self.ok(
            outputs=(config.knowledge_graph_path,),
            entities=len(kg.entities),
            relations=len(kg.relations),
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from core.pipeline import PipelineRunner
    PipelineRunner([ExtractGraphStage()]).run(PipelineConfig.from_env())


if __name__ == "__main__":
    main()
