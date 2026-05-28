"""GraphRAG-Paper harness core.

The *spine* of the pipeline: typed data contracts (`schemas`), centralized
settings (`config`), the stage protocol (`stage`), artifact IO (`artifacts`),
and the orchestrating runner (`pipeline`).

Design rule: nothing in `core` imports a concrete stage. Stages depend on
`core`; the composition root (`run_pipeline.py`) wires them together. This
keeps the dependency graph acyclic.
"""

from __future__ import annotations

from core.config import PipelineConfig
from core.pipeline import PipelineRunner
from core.stage import Stage, StageReport, StageStatus

__all__ = [
    "PipelineConfig",
    "PipelineRunner",
    "Stage",
    "StageReport",
    "StageStatus",
]
