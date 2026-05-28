"""
GraphRAG-Paper - B-M1 - eval/agent_eval.py
--------------------------------------------------
Score the Phase B agent on the SAME question set and SAME RAGAS judge as the
Phase A baseline, so the two are directly comparable. Where Phase A evaluated
each question in both global and local modes, the agent routes each question to
one mode (global/local/vector) and answers once; we score that single stream.

Inputs:  data/eval/questions.json  (+ knowledge_graph + vector index via the agent)
Outputs: data/eval/report_phaseB.json
Compare: compare_phase_a_b() lines this up against data/eval/baseline_phaseA.json.

RAGAS scoring is reused from ragas_eval (_ragas_score), so the judge/embeddings
are identical to the baseline.
"""

from __future__ import annotations

import logging
import os

from core.artifacts import read_json, write_json
from core.config import PipelineConfig
from core.schemas import EvalRecord, EvalReport
from core.stage import Stage, StageReport
from eval.ragas_eval import EXPECTED_METRICS, MIN_METRIC_COVERAGE, _ragas_score

log = logging.getLogger("agent_eval")

AGENT_GROUP = "agent"


# ----------------------------- coverage -----------------------------
def _agent_coverage(records: list[EvalRecord]) -> dict[str, float]:
    """Fraction of questions with a valid (non-dropped) score, per metric.

    The agent is a single answer stream, so coverage is over one group (unlike
    the baseline's per-mode coverage). A low value means RAGAS failed on many
    questions rather than genuinely scoring zero.
    """
    n = len(records)
    coverage: dict[str, float] = {}
    for metric in EXPECTED_METRICS:
        valid = sum(1 for r in records if metric in r.metrics)
        coverage[metric] = (valid / n) if n else 0.0
    return coverage


# ----------------------------- core -----------------------------
def evaluate_agent(config: PipelineConfig) -> EvalReport:
    """Answer each question with the agent, then score with RAGAS."""
    from agent.graph import run_agent

    questions = read_json(config.eval_dataset_path)
    records: list[dict] = []
    for i, q in enumerate(questions, 1):
        result = run_agent(q["question"], config)
        records.append({
            "question": q["question"],
            "answer": result.answer,
            "contexts": list(result.contexts),
            "ground_truth": q["ground_truth"],
            "route": result.mode,                      # the per-question routed mode
            "sources_retrieved": list(result.sources),
        })
        log.info("[%d/%d] route=%s : %s", i, len(questions), result.mode, q["question"][:50])

    scores = _ragas_score({AGENT_GROUP: records})
    per_metric = scores.get(AGENT_GROUP, {})

    eval_records: list[EvalRecord] = []
    for i, rec in enumerate(records):
        # Drop NaN so the report honestly reflects which metrics failed.
        metrics_for_q = {
            name: vals[i]
            for name, vals in per_metric.items()
            if i < len(vals) and vals[i] == vals[i]
        }
        eval_records.append(EvalRecord(
            question=rec["question"],
            answer=rec["answer"],
            mode=rec["route"],  # type: ignore[arg-type]
            contexts=tuple(rec["contexts"]),
            ground_truth=rec["ground_truth"],
            metrics=metrics_for_q,
        ))

    aggregate: dict[str, float] = {}
    for name, vals in per_metric.items():
        valid = [v for v in vals if v == v]  # filter NaN
        if valid:
            aggregate[f"{AGENT_GROUP}_{name}"] = sum(valid) / len(valid)

    return EvalReport(
        dataset=config.eval_dataset_path.name,
        n=len(questions),
        aggregate=aggregate,
        records=tuple(eval_records),
    )


# ----------------------------- comparison -----------------------------
def compare_phase_a_b(config: PipelineConfig) -> list[dict]:
    """Per-metric rows: Phase A (global/local) vs Phase B agent, with delta.

    delta is the agent minus the better of the two Phase A modes (the toughest
    bar). Missing values stay None instead of being coerced to zero.
    """
    a = read_json(config.baseline_report_path).get("aggregate", {})
    b = read_json(config.phaseB_report_path).get("aggregate", {})
    rows: list[dict] = []
    for metric in EXPECTED_METRICS:
        a_global = a.get(f"global_{metric}")
        a_local = a.get(f"local_{metric}")
        b_agent = b.get(f"{AGENT_GROUP}_{metric}")
        available = [v for v in (a_global, a_local) if v is not None]
        a_best = max(available) if available else None
        delta = (b_agent - a_best) if (b_agent is not None and a_best is not None) else None
        rows.append({
            "metric": metric, "a_global": a_global, "a_local": a_local,
            "a_best": a_best, "b_agent": b_agent, "delta": delta,
        })
    return rows


# ----------------------------- stage -----------------------------
class AgentEvalStage(Stage):
    name = "agent_eval"
    milestone = "B-M1"
    requires = ("vector_index",)

    def run(self, config: PipelineConfig) -> StageReport:
        from search.vector import _index_exists

        if not config.knowledge_graph_path.exists():
            return self.skipped("no knowledge_graph.json (build the graph first)")
        if not _index_exists(config):
            return self.skipped("no vector index (run vector_index first)")
        if not config.eval_dataset_path.exists():
            return self.skipped("no questions.json (run the eval stage first)")
        if not config.allow_network:
            return self.skipped(
                "network gated; pass --allow-network or set GRAPHRAG_ALLOW_NETWORK=1"
            )
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return self.skipped(
                "ANTHROPIC_API_KEY not set (agent + RAGAS judge both run on Claude)"
            )
        if config.phaseB_report_path.exists() and not config.force:
            return self.skipped(
                f"{config.phaseB_report_path.name} exists (use --force to re-evaluate)"
            )

        report = evaluate_agent(config)

        # Same honesty guard as the baseline: refuse to write a contaminated report.
        coverage = _agent_coverage(report.records)
        weak = {m: v for m, v in coverage.items() if v < MIN_METRIC_COVERAGE}
        if weak:
            detail = ", ".join(f"agent_{m}={v:.0%}" for m, v in sorted(weak.items()))
            return self.failed(
                f"RAGAS coverage below {MIN_METRIC_COVERAGE:.0%} for: {detail} "
                "— not writing report_phaseB.json (fix credits and re-run with --force)"
            )

        write_json(config.phaseB_report_path, report)
        agg_short = {k: round(v, 3) for k, v in report.aggregate.items()}
        return self.ok(
            outputs=(config.phaseB_report_path,),
            n=report.n,
            coverage_min=round(min(coverage.values()), 2),
            **agg_short,
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from core.pipeline import PipelineRunner

    PipelineRunner([AgentEvalStage()]).run(PipelineConfig.from_env())


if __name__ == "__main__":
    main()
