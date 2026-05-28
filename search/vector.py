"""
GraphRAG-Paper - B-M1 - search/vector.py
--------------------------------------------------
Vector (dense passage) retrieval over the corpus, the third search mode the
Phase B router can pick (alongside global / local). Where global reasons over
abstract community summaries and local walks the entity subgraph, vector search
pulls *verbatim paper passages* — which is what the Phase A baseline lacked for
the many fact-specific questions (numbers, dataset counts, scores).

Index: each corpus doc's abstract/intro/related_work is chunked, embedded with a
local fastembed model (no API cost), and stored in a persistent Chroma index
under data/vector/. Retrieval embeds the query and returns the top-k passages.

Phase A's search/engine.py is intentionally left untouched so the baseline stays
reproducible; this module is a separate retrieval path the agent composes.
"""

from __future__ import annotations

import logging
import shutil

from core.artifacts import read_json
from core.config import PipelineConfig
from core.schemas import SearchResult
from core.stage import Stage, StageReport

# ----------------------------- constants -----------------------------
COLLECTION = "rag_papers"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"   # local fastembed, same as A-M5 RAGAS
CHUNK_CHARS = 1000
CHUNK_OVERLAP = 150
VECTOR_K = 8
SECTIONS = ("abstract", "intro", "related_work")
ANSWER_MAX_TOKENS = 800

VECTOR_PROMPT = """You answer questions about retrieval-augmented generation (RAG) research using passages retrieved from the source papers.

Use ONLY the provided passages. Be concrete: cite specific methods, models, datasets, metrics, and numbers when the passages contain them. If the passages do not contain the answer, say so briefly."""

log = logging.getLogger("vector")


# ----------------------------- chunking -----------------------------
def _chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping fixed-size windows. Empty text -> no chunks."""
    text = (text or "").strip()
    if not text:
        return []
    step = max(1, size - overlap)
    chunks: list[str] = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + size])
        if i + size >= len(text):
            break
        i += step
    return chunks


def _chunk_doc(doc: dict) -> list[tuple[str, dict]]:
    """Chunk a corpus doc's sections into (text, metadata) pairs."""
    paper_id = doc.get("paper_id")
    title = doc.get("title") or paper_id
    out: list[tuple[str, dict]] = []
    for section in SECTIONS:
        for idx, chunk in enumerate(_chunk_text(doc.get(section) or "")):
            out.append((
                chunk,
                {"paper_id": paper_id, "title": title, "section": section, "chunk_idx": idx},
            ))
    return out


# ----------------------------- chroma store -----------------------------
def _embeddings():
    from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

    return FastEmbedEmbeddings(model_name=EMBED_MODEL)


def _store(config: PipelineConfig, embeddings=None):
    from chromadb.config import Settings
    from langchain_chroma import Chroma

    return Chroma(
        collection_name=COLLECTION,
        embedding_function=embeddings or _embeddings(),
        persist_directory=str(config.vector_dir),
        client_settings=Settings(anonymized_telemetry=False),
    )


def _index_exists(config: PipelineConfig) -> bool:
    """True if a persistent Chroma index has been written under data/vector/."""
    return (config.vector_dir / "chroma.sqlite3").exists()


# ----------------------------- build -----------------------------
def build_index(config: PipelineConfig) -> int:
    """(Re)build the vector index from data/corpus/*.json. Returns chunk count."""
    corpus_files = sorted(config.corpus_dir.glob("*.json"))
    texts: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []
    for path in corpus_files:
        doc = read_json(path)
        for text, meta in _chunk_doc(doc):
            texts.append(text)
            metadatas.append(meta)
            ids.append(f"{meta['paper_id']}:{meta['section']}:{meta['chunk_idx']}")

    # Fresh build: drop any prior index so a rebuild can't accumulate duplicates.
    shutil.rmtree(config.vector_dir, ignore_errors=True)
    config.vector_dir.mkdir(parents=True, exist_ok=True)

    if not texts:
        return 0
    store = _store(config)
    store.add_texts(texts=texts, metadatas=metadatas, ids=ids)
    log.info("indexed %d chunks from %d papers", len(texts), len(corpus_files))
    return len(texts)


# ----------------------------- retrieve / search -----------------------------
def vector_retrieve(query: str, config: PipelineConfig, k: int = VECTOR_K) -> list[dict]:
    """Top-k passages for the query as {text, paper_id, title, section, chunk_idx}."""
    store = _store(config)
    docs = store.similarity_search(query, k=k)
    return [{"text": d.page_content, **d.metadata} for d in docs]


def vector_search(query: str, config: PipelineConfig, k: int = VECTOR_K) -> SearchResult:
    """Retrieve passages and answer the query with an LLM grounded in them."""
    from search.engine import _llm_answer  # reuse Phase A's Claude answer helper

    hits = vector_retrieve(query, config, k)
    if not hits:
        return SearchResult(
            query=query, mode="vector",
            answer="(vector index empty — run the vector_index stage first)",
        )
    blocks = [f"## {h['title']} ({h['section']})\n{h['text']}" for h in hits]
    context = "\n\n".join(blocks)
    answer = _llm_answer(query, context, VECTOR_PROMPT)
    # Unique paper_ids, retrieval order preserved.
    sources = tuple(dict.fromkeys(h["paper_id"] for h in hits))
    return SearchResult(
        query=query, mode="vector", answer=answer, contexts=(context,), sources=sources,
    )


# ----------------------------- stage -----------------------------
class BuildVectorIndexStage(Stage):
    """Build the dense-passage index. Offline: fastembed runs locally."""

    name = "vector_index"
    milestone = "B-M1"
    requires = ("build_corpus",)

    def run(self, config: PipelineConfig) -> StageReport:
        corpus_files = sorted(config.corpus_dir.glob("*.json"))
        if not corpus_files:
            return self.skipped("no data/corpus/*.json (run build_corpus first)")
        if _index_exists(config) and not config.force:
            return self.skipped("vector index exists (use --force to rebuild)")
        n = build_index(config)
        if n == 0:
            return self.failed("corpus present but produced 0 chunks")
        return self.ok(outputs=(config.vector_dir,), chunks=n, papers=len(corpus_files))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from core.pipeline import PipelineRunner

    PipelineRunner([BuildVectorIndexStage()]).run(PipelineConfig.from_env())


if __name__ == "__main__":
    main()
