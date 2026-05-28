"""Centralized, immutable pipeline settings.

`PipelineConfig` is the single source of truth for filesystem layout and
cross-cutting toggles (network access, force-rebuild, LLM model). Stage-specific
tuning (keyword weights, etc.) stays inside the stage that owns it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the current working directory (project root) on import,
# so any module reading os.environ (ANTHROPIC_API_KEY, S2_API_KEY, ...) sees it.
load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class PipelineConfig:
    """Immutable settings + derived artifact paths."""

    root: Path
    allow_network: bool = False  # gate live Semantic Scholar / arXiv calls
    force: bool = False  # rebuild artifacts even if present
    llm_model: str = "gpt-4o-mini"  # placeholder for graph/search/eval stages

    # ----------------------- derived artifact paths -----------------------
    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def corpus_dir(self) -> Path:
        return self.data_dir / "corpus"

    @property
    def graph_dir(self) -> Path:
        return self.data_dir / "graph"

    @property
    def eval_dir(self) -> Path:
        return self.data_dir / "eval"

    @property
    def vector_dir(self) -> Path:
        return self.data_dir / "vector"  # Chroma persist dir (B-M1 vector search)

    @property
    def paper_list_path(self) -> Path:
        return self.data_dir / "paper_list.json"

    @property
    def knowledge_graph_path(self) -> Path:
        return self.graph_dir / "knowledge_graph.json"

    @property
    def eval_dataset_path(self) -> Path:
        return self.eval_dir / "questions.json"

    @property
    def eval_report_path(self) -> Path:
        return self.eval_dir / "report.json"

    @property
    def baseline_report_path(self) -> Path:
        return self.eval_dir / "baseline_phaseA.json"  # frozen Phase A reference

    @property
    def phaseB_report_path(self) -> Path:
        return self.eval_dir / "report_phaseB.json"  # agent (B-M1+) eval output

    def ensure_dirs(self) -> None:
        for d in (
            self.data_dir, self.raw_dir, self.corpus_dir,
            self.graph_dir, self.eval_dir, self.vector_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls, root: Path | str | None = None, **overrides) -> "PipelineConfig":
        """Build config from environment variables, with explicit overrides on top.

        Recognized env vars:
          GRAPHRAG_ALLOW_NETWORK, GRAPHRAG_FORCE, GRAPHRAG_LLM_MODEL
        """
        resolved_root = Path(root) if root is not None else Path(__file__).resolve().parent.parent
        settings: dict = {
            "root": resolved_root,
            "allow_network": _env_bool("GRAPHRAG_ALLOW_NETWORK", False),
            "force": _env_bool("GRAPHRAG_FORCE", False),
            "llm_model": os.environ.get("GRAPHRAG_LLM_MODEL", "gpt-4o-mini"),
        }
        settings.update(overrides)
        return cls(**settings)


__all__ = ["PipelineConfig"]
