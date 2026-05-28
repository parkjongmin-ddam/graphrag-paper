"""The stage contract every pipeline step implements.

A Stage reads its inputs from artifacts, does its work, writes its outputs,
and returns a StageReport. Stages must be *honest*: when their real logic is
not implemented yet they return STUB (not fake data); when inputs are missing
they return SKIPPED. The runner relies on stages not raising for these
expected conditions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Mapping

from core.config import PipelineConfig


class StageStatus(str, Enum):
    OK = "ok"            # real work ran and produced outputs
    STUB = "stub"        # domain logic not implemented yet (honest placeholder)
    SKIPPED = "skipped"  # inputs absent / already up to date
    FAILED = "failed"    # unexpected error


@dataclass(frozen=True)
class StageReport:
    stage: str
    status: StageStatus
    detail: str = ""
    outputs: tuple[Path, ...] = ()
    counts: Mapping[str, int] = field(default_factory=dict)


class Stage(ABC):
    """Base class for pipeline stages.

    Subclasses set the class attributes and implement run(). The helper
    methods keep report construction terse and consistent.
    """

    name: ClassVar[str] = "stage"
    milestone: ClassVar[str] = "?"
    requires: ClassVar[tuple[str, ...]] = ()

    @abstractmethod
    def run(self, config: PipelineConfig) -> StageReport:
        """Execute the stage and return an honest report."""

    # ------------------------- report helpers -------------------------
    def _report(
        self,
        status: StageStatus,
        detail: str = "",
        outputs: tuple[Path, ...] = (),
        counts: Mapping[str, int] | None = None,
    ) -> StageReport:
        return StageReport(self.name, status, detail, tuple(outputs), dict(counts or {}))

    def ok(self, detail: str = "", outputs: tuple[Path, ...] = (), **counts: int) -> StageReport:
        return self._report(StageStatus.OK, detail, outputs, counts)

    def stub(self, detail: str = "", **counts: int) -> StageReport:
        return self._report(StageStatus.STUB, detail, (), counts)

    def skipped(self, detail: str = "", **counts: int) -> StageReport:
        return self._report(StageStatus.SKIPPED, detail, (), counts)

    def failed(self, detail: str = "", **counts: int) -> StageReport:
        return self._report(StageStatus.FAILED, detail, (), counts)


__all__ = ["Stage", "StageReport", "StageStatus"]
