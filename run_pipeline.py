"""
GraphRAG-Paper pipeline CLI - the composition root.

Wires the ordered stages into a runner and exposes a small CLI to run the whole
pipeline or a subset. Importing this module pulls in every stage; `core` itself
stays stage-agnostic so the dependency graph has no cycles.

Examples:
    python run_pipeline.py --list
    python run_pipeline.py                       # run all (network gated off)
    python run_pipeline.py --from extract_sections --to build_corpus
    python run_pipeline.py --only collect --allow-network --force
"""

from __future__ import annotations

import argparse
import logging
import sys

from core import PipelineConfig, PipelineRunner
from core.stage import StageStatus
from eval.agent_eval import AgentEvalStage
from eval.ragas_eval import EvalStage
from graph.communities import CommunityStage
from graph.extract import ExtractGraphStage
from ingest.build_corpus import BuildCorpusStage
from ingest.collect import CollectStage
from ingest.extract_sections import ExtractSectionsStage
from search.engine import SearchStage
from search.vector import BuildVectorIndexStage


def build_runner() -> PipelineRunner:
    """The canonical end-to-end pipeline, in execution order."""
    return PipelineRunner(
        [
            CollectStage(),          # A-M0
            ExtractSectionsStage(),  # A-M0
            BuildCorpusStage(),      # A-M0
            ExtractGraphStage(),     # A-M1
            CommunityStage(),        # A-M2/M3
            SearchStage(),           # A-M4
            EvalStage(),             # A-M5
            BuildVectorIndexStage(), # B-M1 (offline: local fastembed)
            AgentEvalStage(),        # B-M1 (agent vs baseline)
        ]
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="GraphRAG-Paper pipeline harness")
    p.add_argument("--only", nargs="+", metavar="STAGE", help="run only these stage(s)")
    p.add_argument("--from", dest="start", metavar="STAGE", help="start from this stage")
    p.add_argument("--to", dest="stop", metavar="STAGE", help="stop after this stage")
    p.add_argument("--strict", action="store_true", help="halt on first failed stage")
    p.add_argument("--allow-network", action="store_true", help="permit live API calls (collect)")
    p.add_argument("--force", action="store_true", help="rebuild artifacts even if present")
    p.add_argument("--list", action="store_true", help="list stages and exit")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args(argv)
    runner = build_runner()

    if args.list:
        print("Pipeline stages (in order):")
        for stage in runner.stages:
            print(f"  {stage.milestone:6} {stage.name}")
        return 0

    overrides: dict = {}
    if args.allow_network:
        overrides["allow_network"] = True
    if args.force:
        overrides["force"] = True
    config = PipelineConfig.from_env(**overrides)

    reports = runner.run(
        config, only=args.only, start=args.start, stop=args.stop, strict=args.strict
    )
    failed = sum(1 for r in reports if r.status is StageStatus.FAILED)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
