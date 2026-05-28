"""
GraphRAG-Paper - Judge ablation (second-judge fairness check)
--------------------------------------------------
Re-scores the *existing* baseline and agent records (same answers, same
retrieved contexts, same ground truths) with a different judge model family —
OpenAI gpt-4o-mini — to test whether the Claude judge is biased toward Claude-
generated answers (self-preference). The agent is NOT re-run; we hold every
variable fixed except the judge, so any score change is attributable to the
judge alone.

Inputs:
  data/eval/baseline_phaseA.json   (Phase A, Claude judge)
  data/eval/report_phaseB.json     (Phase B agent, Claude judge)

Outputs:
  data/eval/baseline_phaseA_openai_judge.json
  data/eval/report_phaseB_openai_judge.json

Run from project root:
    python eval/judge_ablation.py
"""

from __future__ import annotations

import json
import logging
import os
import sys

from core.artifacts import write_json
from core.config import PipelineConfig
from core.schemas import EvalRecord, EvalReport
from eval.ragas_eval import EXPECTED_METRICS, _ragas_score

OPENAI_JUDGE_MODEL = "gpt-4o-mini"
OPENAI_MAX_TOKENS = 2048
AGENT_GROUP = "agent"

log = logging.getLogger("judge_ablation")


def _openai_judge():
    """Build an OpenAI judge wrapped for RAGAS; mirrors the Claude path's structure."""
    from langchain_openai import ChatOpenAI
    from ragas.llms import LangchainLLMWrapper

    return LangchainLLMWrapper(
        ChatOpenAI(model=OPENAI_JUDGE_MODEL, temperature=0, max_tokens=OPENAI_MAX_TOKENS)
    )


def rejudge_baseline(config: PipelineConfig, llm) -> EvalReport:
    """Re-judge Phase A baseline (global + local modes) with the given LLM."""
    src = json.loads(config.baseline_report_path.read_text(encoding="utf-8"))
    records_by_mode: dict[str, list[dict]] = {"global": [], "local": []}
    for r in src["records"]:
        records_by_mode[r["mode"]].append({
            "question": r["question"],
            "answer": r["answer"],
            "contexts": list(r["contexts"]),
            "ground_truth": r["ground_truth"],
            "mode": r["mode"],
        })
    log.info(
        "rejudging baseline: global=%d local=%d",
        len(records_by_mode["global"]), len(records_by_mode["local"]),
    )
    scores = _ragas_score(records_by_mode, llm=llm)

    eval_records: list[EvalRecord] = []
    aggregate: dict[str, float] = {}
    for mode, recs in records_by_mode.items():
        per_metric = scores.get(mode, {})
        for i, rec in enumerate(recs):
            metrics_for_q = {
                name: vals[i]
                for name, vals in per_metric.items()
                if i < len(vals) and vals[i] == vals[i]   # drop NaN honestly
            }
            eval_records.append(EvalRecord(
                question=rec["question"],
                answer=rec["answer"],
                mode=rec["mode"],
                contexts=tuple(rec["contexts"]),
                ground_truth=rec["ground_truth"],
                metrics=metrics_for_q,
            ))
        for name, vals in per_metric.items():
            valid = [v for v in vals if v == v]
            if valid:
                aggregate[f"{mode}_{name}"] = sum(valid) / len(valid)
    return EvalReport(
        dataset=src.get("dataset", config.eval_dataset_path.name),
        n=src["n"],
        aggregate=aggregate,
        records=tuple(eval_records),
    )


def rejudge_agent(config: PipelineConfig, llm) -> EvalReport:
    """Re-judge Phase B agent (single 'agent' group) with the given LLM."""
    src = json.loads(config.phaseB_report_path.read_text(encoding="utf-8"))
    records = [{
        "question": r["question"],
        "answer": r["answer"],
        "contexts": list(r["contexts"]),
        "ground_truth": r["ground_truth"],
        "mode": r["mode"],
    } for r in src["records"]]
    log.info("rejudging agent: n=%d", len(records))
    scores = _ragas_score({AGENT_GROUP: records}, llm=llm)
    per_metric = scores.get(AGENT_GROUP, {})

    eval_records: list[EvalRecord] = []
    for i, rec in enumerate(records):
        metrics_for_q = {
            name: vals[i]
            for name, vals in per_metric.items()
            if i < len(vals) and vals[i] == vals[i]
        }
        eval_records.append(EvalRecord(
            question=rec["question"],
            answer=rec["answer"],
            mode=rec["mode"],
            contexts=tuple(rec["contexts"]),
            ground_truth=rec["ground_truth"],
            metrics=metrics_for_q,
        ))
    aggregate: dict[str, float] = {}
    for name, vals in per_metric.items():
        valid = [v for v in vals if v == v]
        if valid:
            aggregate[f"{AGENT_GROUP}_{name}"] = sum(valid) / len(valid)
    return EvalReport(
        dataset=src.get("dataset", config.eval_dataset_path.name),
        n=src["n"],
        aggregate=aggregate,
        records=tuple(eval_records),
    )


def _baseline_best(agg: dict, metric: str) -> float | None:
    vals = [agg.get(f"global_{metric}"), agg.get(f"local_{metric}")]
    vals = [v for v in vals if v is not None]
    return max(vals) if vals else None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = PipelineConfig.from_env()

    if not os.environ.get("OPENAI_API_KEY"):
        log.error("OPENAI_API_KEY not set — add it to .env or env and rerun")
        sys.exit(1)
    if not config.baseline_report_path.exists() or not config.phaseB_report_path.exists():
        log.error("baseline_phaseA.json or report_phaseB.json missing — run the pipeline first")
        sys.exit(1)

    llm = _openai_judge()
    log.info(
        "judge ablation with %s (different model family from the Claude default)",
        OPENAI_JUDGE_MODEL,
    )

    baseline = rejudge_baseline(config, llm)
    out_baseline = config.eval_dir / "baseline_phaseA_openai_judge.json"
    write_json(out_baseline, baseline)
    log.info("wrote %s", out_baseline)

    agent = rejudge_agent(config, llm)
    out_agent = config.eval_dir / "report_phaseB_openai_judge.json"
    write_json(out_agent, agent)
    log.info("wrote %s", out_agent)

    # Claude-judged numbers (existing reports) for side-by-side
    claude_base = json.loads(config.baseline_report_path.read_text(encoding="utf-8"))["aggregate"]
    claude_agent = json.loads(config.phaseB_report_path.read_text(encoding="utf-8"))["aggregate"]

    print("\n=== Judge ablation: agent vs baseline_best, by judge (100p, n=40) ===")
    print(
        f"{'metric':<20}{'claude base':>13}{'openai base':>13}"
        f"{'claude agent':>14}{'openai agent':>14}{'Delta(claude)':>15}{'Delta(openai)':>15}"
    )
    for m in EXPECTED_METRICS:
        cb = _baseline_best(claude_base, m)
        ob = _baseline_best(baseline.aggregate, m)
        ca = claude_agent.get(f"agent_{m}")
        oa = agent.aggregate.get(f"agent_{m}")
        dc = (ca - cb) if (ca is not None and cb is not None) else None
        do = (oa - ob) if (oa is not None and ob is not None) else None

        def fmt(v):
            return f"{v:.3f}" if v is not None else "  n/a"

        def fmtd(v):
            return f"{v:+.3f}" if v is not None else "  n/a"

        print(
            f"{m:<20}{fmt(cb):>13}{fmt(ob):>13}"
            f"{fmt(ca):>14}{fmt(oa):>14}{fmtd(dc):>15}{fmtd(do):>15}"
        )


if __name__ == "__main__":
    main()
