"""The orchestrating runner: run an ordered list of stages, report honestly.

The runner never lets a stage crash the process - an unexpected exception is
caught and recorded as FAILED. It supports running a subset (only) or a slice
(start/stop) of the pipeline, and prints a summary table so the end-to-end
shape of the project is visible at a glance.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from core.config import PipelineConfig
from core.stage import Stage, StageReport, StageStatus

log = logging.getLogger("pipeline")

_ICON = {
    StageStatus.OK: "[ok]",
    StageStatus.STUB: "[stub]",
    StageStatus.SKIPPED: "[skip]",
    StageStatus.FAILED: "[FAIL]",
}


class PipelineRunner:
    def __init__(self, stages: Sequence[Stage]) -> None:
        self.stages: list[Stage] = list(stages)

    def stage_names(self) -> list[str]:
        return [s.name for s in self.stages]

    def _select(
        self,
        only: Sequence[str] | None,
        start: str | None,
        stop: str | None,
    ) -> list[Stage]:
        if only:
            wanted = set(only)
            return [s for s in self.stages if s.name in wanted]
        names = self.stage_names()
        lo = names.index(start) if start else 0
        hi = names.index(stop) + 1 if stop else len(names)
        return self.stages[lo:hi]

    def run(
        self,
        config: PipelineConfig,
        *,
        only: Sequence[str] | None = None,
        start: str | None = None,
        stop: str | None = None,
        strict: bool = False,
    ) -> list[StageReport]:
        config.ensure_dirs()
        selected = self._select(only, start, stop)
        reports: list[StageReport] = []
        for stage in selected:
            log.info("running %s (%s)", stage.name, stage.milestone)
            try:
                report = stage.run(config)
            except Exception as exc:  # a stage bug must not take down the harness
                log.exception("stage %s raised", stage.name)
                report = StageReport(
                    stage.name, StageStatus.FAILED, detail=f"{type(exc).__name__}: {exc}"
                )
            reports.append(report)
            self._log_report(report)
            if strict and report.status is StageStatus.FAILED:
                log.error("strict mode: halting at failed stage '%s'", stage.name)
                break
        self._print_summary(reports)
        return reports

    @staticmethod
    def _log_report(r: StageReport) -> None:
        counts = " ".join(f"{k}={v}" for k, v in r.counts.items())
        msg = f"{_ICON[r.status]} {r.stage}: {r.status.value}"
        if r.detail:
            msg += f" - {r.detail}"
        if counts:
            msg += f" [{counts}]"
        log.info(msg)

    @staticmethod
    def _print_summary(reports: Sequence[StageReport]) -> None:
        if not reports:
            log.info("no stages selected")
            return
        width = max(len(r.stage) for r in reports)
        lines = ["", "Pipeline summary", "-" * (width + 16)]
        for r in reports:
            lines.append(f"  {_ICON[r.status]:>7} {r.stage.ljust(width)}  {r.status.value}")
        n_fail = sum(1 for r in reports if r.status is StageStatus.FAILED)
        lines.append("-" * (width + 16))
        lines.append(f"  {len(reports)} stage(s), {n_fail} failed")
        log.info("\n".join(lines))


__all__ = ["PipelineRunner"]
