"""Typed data contracts exchanged between pipeline stages.

These frozen dataclasses are the *interface* of the harness: each stage
consumes and produces them, so the schema here is the single source of truth
for what flows from ingest -> graph -> search -> eval. Keep this file
dependency-free (stdlib only) so every layer can import it cheaply.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# Domain-specific schema (see README corpus policy).
EntityType = Literal[
    "Method", "Model", "Dataset", "Metric", "Task", "Author", "Institution", "Paper"
]
RelationType = Literal[
    "USES", "EVALUATED_ON", "IMPROVES", "OUTPERFORMS", "COMBINES", "PROPOSED_BY", "CITES"
]
SearchMode = Literal["global", "local", "vector"]
SectionSource = Literal["latex", "grobid", "abstract_only"]


@dataclass(frozen=True)
class PaperRef:
    """A selected paper from collect (A-M0). Mirrors paper_list.json."""

    paper_id: str
    arxiv_id: str | None
    title: str | None
    abstract: str | None
    year: int | None
    citation_count: int | None
    score: float | None = None
    fields: tuple[str, ...] = ()
    references: tuple[str, ...] = ()  # outbound paperIds (cited by this paper)


@dataclass(frozen=True)
class RawSections:
    """Sections extracted from a paper's source (A-M0 extract_sections)."""

    arxiv_id: str
    abstract: str
    intro: str
    related_work: str
    source: SectionSource


@dataclass(frozen=True)
class CorpusDoc:
    """A cleaned, per-paper corpus document (A-M0 build_corpus)."""

    paper_id: str
    arxiv_id: str | None
    title: str
    year: int | None
    authors: tuple[str, ...]
    abstract: str
    intro: str
    related_work: str
    citations: tuple[str, ...]  # referenced paper_ids


@dataclass(frozen=True)
class Entity:
    """A typed knowledge-graph node (A-M1)."""

    id: str
    name: str
    type: EntityType
    description: str = ""
    source_papers: tuple[str, ...] = ()


@dataclass(frozen=True)
class Relation:
    """A typed knowledge-graph edge (A-M1)."""

    source_id: str
    target_id: str
    type: RelationType
    description: str = ""
    source_papers: tuple[str, ...] = ()


@dataclass(frozen=True)
class Community:
    """A detected community with its summary (A-M2 Leiden + A-M3 summary)."""

    id: str
    level: int
    entity_ids: tuple[str, ...]
    title: str = ""
    summary: str = ""


@dataclass(frozen=True)
class KnowledgeGraph:
    """The assembled graph consumed by search (A-M2..M4)."""

    entities: tuple[Entity, ...] = ()
    relations: tuple[Relation, ...] = ()
    communities: tuple[Community, ...] = ()


@dataclass(frozen=True)
class SearchResult:
    """The answer + grounding produced by a search query (A-M4)."""

    query: str
    mode: SearchMode
    answer: str
    contexts: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvalRecord:
    """A single graded question (A-M5 RAGAS)."""

    question: str
    answer: str
    mode: SearchMode = "global"  # which search mode produced this answer
    contexts: tuple[str, ...] = ()
    ground_truth: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class EvalReport:
    """Aggregate evaluation over a dataset, the RAGAS baseline (A-M5)."""

    dataset: str
    n: int
    aggregate: dict[str, float] = field(default_factory=dict)
    records: tuple[EvalRecord, ...] = ()


__all__ = [
    "EntityType", "RelationType", "SearchMode", "SectionSource",
    "PaperRef", "RawSections", "CorpusDoc",
    "Entity", "Relation", "Community", "KnowledgeGraph",
    "SearchResult", "EvalRecord", "EvalReport",
]
