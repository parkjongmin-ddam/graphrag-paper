"""
GraphRAG-Paper - A-M0 - build_corpus.py
--------------------------------------------------
Turn extract_sections output (data/raw/) into clean per-paper corpus docs.

Output: data/corpus/<paper_id>.json (input to A-M1 entity extraction).
"""

from __future__ import annotations

import logging
import re

from core.artifacts import load_paper_list, read_json, write_json
from core.config import PipelineConfig
from core.schemas import CorpusDoc, PaperRef
from core.stage import Stage, StageReport

# Pylatexenc renders \cite{...} as the literal token "<cit.>"; rewrite to "[cite]"
# so downstream LLM prompts don't anchor on an HTML-ish marker.
_CIT_RE = re.compile(r"<cit\.>")
_WS_RE = re.compile(r"[ \t]+")
_NL_RE = re.compile(r"\n{3,}")

log = logging.getLogger("build_corpus")


def _clean(text: str) -> str:
    if not text:
        return ""
    s = _CIT_RE.sub("[cite]", text)
    s = _WS_RE.sub(" ", s)
    s = _NL_RE.sub("\n\n", s)
    return s.strip()


def _papers_by_arxiv(papers: list[PaperRef]) -> dict[str, PaperRef]:
    return {p.arxiv_id: p for p in papers if p.arxiv_id}


def build_corpus(config: PipelineConfig) -> list[CorpusDoc]:
    """Read data/raw/*.json + paper_list, clean, write data/corpus/*.json, return them.

    Assumes data/raw/*.json exists (the stage gates on this).
    `authors` and `citations` are placeholders (()) — populated by a later
    enrichment stage when CITES relations and Author entities are needed.
    """
    by_arxiv = _papers_by_arxiv(load_paper_list(config))
    config.corpus_dir.mkdir(parents=True, exist_ok=True)
    docs: list[CorpusDoc] = []

    for raw_path in sorted(config.raw_dir.glob("*.json")):
        raw = read_json(raw_path)
        arxiv_id = raw.get("arxiv_id")
        if not arxiv_id:
            log.warning("%s: missing arxiv_id, skipping", raw_path.name)
            continue
        ref = by_arxiv.get(arxiv_id)
        if ref is None:
            log.warning("%s: arxiv_id not in paper_list, skipping", arxiv_id)
            continue

        abstract = _clean(raw.get("abstract") or ref.abstract or "")
        intro = _clean(raw.get("intro") or "")
        related = _clean(raw.get("related_work") or "")
        if not (abstract or intro or related):
            log.warning("%s: no usable text, skipping", arxiv_id)
            continue

        doc = CorpusDoc(
            paper_id=ref.paper_id,
            arxiv_id=arxiv_id,
            title=ref.title or "",
            year=ref.year,
            authors=(),
            abstract=abstract,
            intro=intro,
            related_work=related,
            citations=ref.references,
        )
        out_path = config.corpus_dir / f"{ref.paper_id}.json"
        write_json(out_path, doc)
        docs.append(doc)
        log.info(
            "%s -> %s [abstract=%d intro=%d related=%d]",
            arxiv_id, out_path.name, len(abstract), len(intro), len(related),
        )
    log.info("wrote %d corpus docs", len(docs))
    return docs


class BuildCorpusStage(Stage):
    name = "build_corpus"
    milestone = "A-M0"
    requires = ("extract_sections",)

    def run(self, config: PipelineConfig) -> StageReport:
        raw_files = sorted(config.raw_dir.glob("*.json"))
        if not raw_files:
            return self.skipped("no data/raw/*.json (run extract_sections first)")
        docs = build_corpus(config)
        return self.ok(outputs=(config.corpus_dir,), docs=len(docs))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from core.pipeline import PipelineRunner
    PipelineRunner([BuildCorpusStage()]).run(PipelineConfig.from_env())


if __name__ == "__main__":
    main()
