"""JSON artifact IO for the pipeline.

Stages persist their outputs as JSON under data/. This module centralizes
(de)serialization so dataclass contracts round-trip consistently. Typed loaders
are provided where a downstream stage actually consumes the artifact; add more
as stages graduate from stub to real.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable

from core.config import PipelineConfig
from core.schemas import PaperRef


def _to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    raise TypeError(f"not JSON-serializable: {type(obj).__name__}")


def write_json(path: Path, data: Any) -> Path:
    """Write data (may contain dataclasses) as pretty UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2, default=_to_jsonable)
    path.write_text(text, encoding="utf-8")
    return path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_records(path: Path, items: Iterable[Any]) -> Path:
    """Write an iterable of dataclasses (or dicts) as a JSON array."""
    rows = [
        asdict(x) if is_dataclass(x) and not isinstance(x, type) else x
        for x in items
    ]
    return write_json(path, rows)


def load_paper_list(config: PipelineConfig) -> list[PaperRef]:
    """Load data/paper_list.json into typed PaperRefs (empty if absent)."""
    path = config.paper_list_path
    if not path.exists():
        return []
    return [
        PaperRef(
            paper_id=row.get("paper_id"),
            arxiv_id=row.get("arxiv_id"),
            title=row.get("title"),
            abstract=row.get("abstract"),
            year=row.get("year"),
            citation_count=row.get("citation_count"),
            score=row.get("score"),
            fields=tuple(row.get("fields") or ()),
            references=tuple(row.get("references") or ()),
        )
        for row in read_json(path)
    ]


__all__ = ["write_json", "read_json", "write_records", "load_paper_list"]
