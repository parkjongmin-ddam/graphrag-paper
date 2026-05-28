"""
GraphRAG-Paper - Evaluate on the human-authored question subset
--------------------------------------------------
Runs Phase A baseline (global + local) and the Phase B agent over the human
questions, then scores BOTH with the Claude judge AND with the OpenAI judge for
a cross-judge check on this independent eval set.

Inputs:  data/eval/questions_human.json (parsed from the filled draft)
Outputs: data/eval/{baseline,agent}_human_{claude,openai}.json
         (records contain answer/contexts/ground_truth; aggregate keys
          mirror the synthetic-eval reports.)

Prints synthetic-vs-human delta comparison so you can see whether the agent's
advantage generalizes to questions a human asked.

Run from project root:
    python -m eval.eval_human
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from core.artifacts import write_json
from core.config import PipelineConfig
from core.schemas import EvalRecord, EvalReport
from eval.judge_ablation import _openai_judge
from eval.ragas_eval import EXPECTED_METRICS, _ragas_score

AGENT_GROUP = "agent"
log = logging.getLogger("eval_human")


def _run_baseline(config: PipelineConfig, questions: list[dict]) -> dict[str, list[dict]]:
    """Phase A: answer each question in global + local modes (frozen baseline)."""
    from search.engine import search

    records_by_mode: dict[str, list[dict]] = {"global": [], "local": []}
    for i, q in enumerate(questions, 1):
        for mode in ("global", "local"):
            r = search(q["question"], config, mode=mode)
            records_by_mode[mode].append({
                "question": q["question"],
                "answer": r.answer,
                "contexts": list(r.contexts),
                "ground_truth": q["ground_truth"],
                "mode": mode,
                "category": q.get("category"),
            })
        log.info("[%d/%d] baseline answered: %s", i, len(questions), q["question"][:60])
    return records_by_mode


def _run_agent(config: PipelineConfig, questions: list[dict]) -> list[dict]:
    """Phase B agent: one answer per question with the routed mode."""
    from agent.graph import run_agent

    records: list[dict] = []
    for i, q in enumerate(questions, 1):
        result = run_agent(q["question"], config)
        records.append({
            "question": q["question"],
            "answer": result.answer,
            "contexts": list(result.contexts),
            "ground_truth": q["ground_truth"],
            "mode": result.mode,
            "category": q.get("category"),
        })
        log.info("[%d/%d] agent route=%s: %s", i, len(questions), result.mode, q["question"][:60])
    return records


def _score_baseline(records_by_mode: dict[str, list[dict]], llm, dataset_name: str) -> EvalReport:
    scores = _ragas_score(records_by_mode, llm=llm)
    eval_records: list[EvalRecord] = []
    aggregate: dict[str, float] = {}
    n = 0
    for mode, recs in records_by_mode.items():
        n = len(recs)  # same n per mode
        per_metric = scores.get(mode, {})
        for i, rec in enumerate(recs):
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
        for name, vals in per_metric.items():
            valid = [v for v in vals if v == v]
            if valid:
                aggregate[f"{mode}_{name}"] = sum(valid) / len(valid)
    return EvalReport(dataset=dataset_name, n=n, aggregate=aggregate, records=tuple(eval_records))


def _score_agent(records: list[dict], llm, dataset_name: str) -> EvalReport:
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
    return EvalReport(dataset=dataset_name, n=len(records), aggregate=aggregate, records=tuple(eval_records))


def _baseline_best(agg: dict, metric: str) -> float | None:
    vals = [agg.get(f"global_{metric}"), agg.get(f"local_{metric}")]
    vals = [v for v in vals if v is not None]
    return max(vals) if vals else None


def _print_comparison(human_b_claude, human_a_claude, human_b_openai, human_a_openai, config):
    """Cross-set, cross-judge delta comparison: synthetic vs human."""
    synth_b = json.loads(config.baseline_report_path.read_text(encoding="utf-8"))["aggregate"]
    synth_a = json.loads(config.phaseB_report_path.read_text(encoding="utf-8"))["aggregate"]
    synth_b_oai = json.loads((config.eval_dir / "baseline_phaseA_openai_judge.json").read_text(encoding="utf-8"))["aggregate"]
    synth_a_oai = json.loads((config.eval_dir / "report_phaseB_openai_judge.json").read_text(encoding="utf-8"))["aggregate"]

    print(f"\n=== Agent − baseline_best delta: synthetic (n=40) vs human (n={human_a_claude.n}) ===")
    hdr = f"{'metric':<20}{'synth claude':>14}{'human claude':>14}{'synth openai':>14}{'human openai':>14}"
    print(hdr)
    print("-" * len(hdr))

    def delta(agent_agg: dict, base_agg: dict, m: str) -> float | None:
        a = agent_agg.get(f"agent_{m}")
        b = _baseline_best(base_agg, m)
        return (a - b) if (a is not None and b is not None) else None

    for m in EXPECTED_METRICS:
        sc = delta(synth_a, synth_b, m)
        hc = delta(human_a_claude.aggregate, human_b_claude.aggregate, m)
        so = delta(synth_a_oai, synth_b_oai, m)
        ho = delta(human_a_openai.aggregate, human_b_openai.aggregate, m)

        def fmt(v):
            return f"{v:+.3f}" if v is not None else "  n/a"

        print(f"{m:<20}{fmt(sc):>14}{fmt(hc):>14}{fmt(so):>14}{fmt(ho):>14}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = PipelineConfig.from_env()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.error("ANTHROPIC_API_KEY not set"); sys.exit(1)
    if not os.environ.get("OPENAI_API_KEY"):
        log.error("OPENAI_API_KEY not set (needed for second-judge cross-check)"); sys.exit(1)
    if not config.knowledge_graph_path.exists():
        log.error("knowledge_graph.json missing — run the pipeline first"); sys.exit(1)

    qpath = config.eval_dir / "questions_human.json"
    if not qpath.exists():
        log.error("%s not found — run `python -m eval.parse_human_draft` after filling the draft", qpath)
        sys.exit(1)
    questions = json.loads(qpath.read_text(encoding="utf-8"))
    log.info("loaded %d human-authored questions", len(questions))

    # Run baseline + agent ONCE; we score the same records under both judges.
    log.info("--- running Phase A baseline (global + local) ---")
    baseline_records = _run_baseline(config, questions)

    log.info("--- running Phase B agent ---")
    agent_records = _run_agent(config, questions)

    # Score with Claude (default RAGAS judge), then OpenAI (cross-check).
    log.info("--- scoring baseline with Claude judge ---")
    b_claude = _score_baseline(baseline_records, llm=None, dataset_name="questions_human.json")
    write_json(config.eval_dir / "baseline_human_claude.json", b_claude)

    log.info("--- scoring agent with Claude judge ---")
    a_claude = _score_agent(agent_records, llm=None, dataset_name="questions_human.json")
    write_json(config.eval_dir / "agent_human_claude.json", a_claude)

    log.info("--- scoring baseline with OpenAI judge (gpt-4o-mini) ---")
    openai_llm = _openai_judge()
    b_openai = _score_baseline(baseline_records, llm=openai_llm, dataset_name="questions_human.json")
    write_json(config.eval_dir / "baseline_human_openai.json", b_openai)

    log.info("--- scoring agent with OpenAI judge ---")
    a_openai = _score_agent(agent_records, llm=openai_llm, dataset_name="questions_human.json")
    write_json(config.eval_dir / "agent_human_openai.json", a_openai)

    _print_comparison(b_claude, a_claude, b_openai, a_openai, config)


if __name__ == "__main__":
    main()
