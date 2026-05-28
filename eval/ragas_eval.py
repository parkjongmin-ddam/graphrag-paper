"""
GraphRAG-Paper - A-M5 - eval/ragas_eval.py
--------------------------------------------------
Phase A baseline: synthesize a small Q&A set from the corpus, answer each
question with both global and local search, score with RAGAS (faithfulness,
answer_relevancy, context_recall, context_precision). The aggregate scores
are the baseline that Phase B's agentic loops will be measured against.

Inputs:  data/corpus/*.json  +  data/graph/knowledge_graph.json
Outputs: data/eval/questions.json  +  data/eval/report.json
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import warnings

from core.artifacts import read_json, write_json
from core.config import PipelineConfig
from core.schemas import EvalRecord, EvalReport
from core.stage import Stage, StageReport

# ----------------------------- constants -----------------------------
GEN_MODEL = "claude-haiku-4-5-20251001"      # same model as A-M1 / A-M3
GEN_MAX_TOKENS = 600
# RAGAS judge runs on Claude (the OpenAI account is out of quota). Embeddings run
# locally via fastembed (ONNX, no torch, no API cost) and are only consumed by
# answer_relevancy; the other three metrics are LLM-only.
RAGAS_LLM_MODEL = "claude-haiku-4-5-20251001"
RAGAS_LLM_MAX_TOKENS = 2048
RAGAS_EMBED_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_N = 20
QUESTION_SEED = 42

# A run is only a trustworthy baseline if RAGAS actually scored most questions.
# evaluate_baseline drops NaN, so a low valid-fraction means the judge failed en
# masse (API outage, credit exhaustion, parse errors) — not genuine zeros. Below
# this per-(mode, metric) coverage the stage fails instead of writing a report
# built from a biased handful of survivors.
EXPECTED_MODES = ("global", "local")
EXPECTED_METRICS = (
    "faithfulness", "answer_relevancy", "context_recall", "context_precision",
)
MIN_METRIC_COVERAGE = 0.8

QUESTION_GEN_PROMPT = """Given a research paper excerpt about retrieval-augmented generation (RAG), generate ONE question that:
- A reader would naturally ask after reading the paper
- Can be answered using specific information in the paper (a method, a dataset, a number, a comparison)
- Is concrete, not "What is the paper about?"

Then provide a 1-2 sentence ground-truth answer grounded ONLY in the excerpt.

Return ONLY a JSON object, no prose, no markdown fence:
{"question": "...", "ground_truth": "..."}"""

log = logging.getLogger("eval")


# ----------------------------- question generation -----------------------------
def _generate_questions(config: PipelineConfig, n: int = DEFAULT_N) -> list[dict]:
    """Sample n corpus docs and ask claude-haiku for one Q+ground-truth each."""
    import anthropic

    corpus_files = sorted(config.corpus_dir.glob("*.json"))
    n = min(n, len(corpus_files))
    random.seed(QUESTION_SEED)
    sampled = random.sample(corpus_files, n)

    client = anthropic.Anthropic()
    out: list[dict] = []
    for i, path in enumerate(sampled, 1):
        doc = read_json(path)
        excerpt = (doc.get("abstract") or "")[:1500]
        if doc.get("intro"):
            excerpt = (excerpt + "\n\n" + doc["intro"][:1500]).strip()
        if not excerpt:
            continue
        try:
            resp = client.messages.create(
                model=GEN_MODEL,
                max_tokens=GEN_MAX_TOKENS,
                system=QUESTION_GEN_PROMPT,
                messages=[{"role": "user", "content": excerpt}],
            )
            raw = "".join(b.text for b in resp.content if b.type == "text")
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                log.warning("[%d/%d] %s: no JSON in response", i, n, doc.get("paper_id"))
                continue
            data = json.loads(m.group(0))
            q = (data.get("question") or "").strip()
            gt = (data.get("ground_truth") or "").strip()
            if not q or not gt:
                continue
            out.append({"question": q, "ground_truth": gt, "source_paper_id": doc["paper_id"]})
            log.info("[%d/%d] generated Q for %s", i, n, doc.get("paper_id"))
        except Exception as e:
            log.exception("[%d/%d] generation failed: %s", i, n, e)
    return out


# ----------------------------- RAGAS scoring -----------------------------
def _ragas_score(
    records_by_mode: dict[str, list[dict]],
    llm=None,
) -> dict[str, dict[str, list[float]]]:
    """Run RAGAS 4 metrics per mode; return {mode: {metric: per_question_scores}}.

    `llm` is an optional pre-built LangchainLLMWrapper. Default (None) builds the
    Claude judge used everywhere else; passing a different wrapper enables judge
    ablation (e.g., OpenAI as a second judge — see eval/judge_ablation.py).
    """
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    from datasets import Dataset
    from langchain_anthropic import ChatAnthropic
    from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
    from langchain_core.embeddings import Embeddings
    from ragas import evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (
        answer_relevancy, context_precision, context_recall, faithfulness,
    )

    class _StrModelEmbeddings(Embeddings):
        """fastembed wrapped so RAGAS telemetry sees a *string* `.model`.

        RAGAS's LangchainEmbeddingsWrapper logs
        `EmbeddingUsageEvent(model=getattr(embeddings, "model", None))` and
        validates that field as `str`. FastEmbedEmbeddings.model is the loaded
        TextEmbedding object, which fails validation and silently NaNs out
        answer_relevancy. Exposing a string `model` sidesteps it without
        touching fastembed internals; the async embed methods are inherited
        from the Embeddings base (run_in_executor over these sync ones).
        """

        def __init__(self, model_name: str):
            self._inner = FastEmbedEmbeddings(model_name=model_name)
            self.model = model_name  # the string RAGAS's usage event expects

        def embed_query(self, text: str) -> list[float]:
            return self._inner.embed_query(text)

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return self._inner.embed_documents(texts)

    if llm is None:
        llm = LangchainLLMWrapper(
            ChatAnthropic(
                model=RAGAS_LLM_MODEL, temperature=0, max_tokens=RAGAS_LLM_MAX_TOKENS
            )
        )
    embed = LangchainEmbeddingsWrapper(_StrModelEmbeddings(RAGAS_EMBED_MODEL))
    metrics = [faithfulness, answer_relevancy, context_recall, context_precision]
    metric_names = ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]

    out: dict[str, dict[str, list[float]]] = {}
    for mode, records in records_by_mode.items():
        ds = Dataset.from_list([
            {
                "user_input": r["question"],
                "response": r["answer"],
                "retrieved_contexts": r["contexts"] or [""],
                "reference": r["ground_truth"],
            }
            for r in records
        ])
        log.info("running RAGAS for mode=%s (n=%d)...", mode, len(records))
        result = evaluate(
            ds,
            metrics=metrics,
            llm=llm,
            embeddings=embed,
            show_progress=False,
            raise_exceptions=False,
        )
        df = result.to_pandas()
        out[mode] = {}
        for name in metric_names:
            if name in df.columns:
                col = df[name].tolist()
                # Preserve NaN so the aggregate step can drop failed metrics honestly
                # rather than silently averaging them as zero.
                out[mode][name] = [float(v) for v in col]
            else:
                log.warning("metric %s missing from RAGAS output", name)
                out[mode][name] = [float("nan")] * len(records)
    return out


# ----------------------------- core -----------------------------
def evaluate_baseline(config: PipelineConfig) -> EvalReport:
    """Search each question in both modes, then score with RAGAS."""
    from search.engine import search

    questions = read_json(config.eval_dataset_path)
    records_by_mode: dict[str, list[dict]] = {"global": [], "local": []}
    for i, q in enumerate(questions, 1):
        for mode in ("global", "local"):
            r = search(q["question"], config, mode=mode)
            records_by_mode[mode].append({
                "question": q["question"],
                "answer": r.answer,
                "contexts": list(r.contexts),
                "ground_truth": q["ground_truth"],
                "source_paper_id": q.get("source_paper_id"),
                "sources_retrieved": list(r.sources),
            })
        log.info("[%d/%d] answered: %s", i, len(questions), q["question"][:60])

    scores_by_mode = _ragas_score(records_by_mode)

    eval_records: list[EvalRecord] = []
    aggregate: dict[str, float] = {}
    for mode, records in records_by_mode.items():
        per_metric = scores_by_mode.get(mode, {})
        for i, rec in enumerate(records):
            # Drop NaN entries so report.json stays valid JSON and so the file
            # honestly reflects which metrics failed.
            metrics_for_q = {
                name: scores[i]
                for name, scores in per_metric.items()
                if i < len(scores) and scores[i] == scores[i]
            }
            eval_records.append(EvalRecord(
                question=rec["question"],
                answer=rec["answer"],
                mode=mode,  # type: ignore[arg-type]
                contexts=tuple(rec["contexts"]),
                ground_truth=rec["ground_truth"],
                metrics=metrics_for_q,
            ))
        for name, scores in per_metric.items():
            valid = [s for s in scores if s == s]  # filter NaN
            if valid:
                aggregate[f"{mode}_{name}"] = sum(valid) / len(valid)

    return EvalReport(
        dataset=config.eval_dataset_path.name,
        n=len(questions),
        aggregate=aggregate,
        records=tuple(eval_records),
    )


# Back-compat alias for the scaffold's name.
evaluate = evaluate_baseline


def _metric_coverage(report: EvalReport) -> dict[str, float]:
    """Fraction of questions that produced a valid score, keyed "<mode>_<metric>".

    evaluate_baseline drops NaN metrics, so this measures how much of the intended
    grid (modes x metrics x questions) actually came back. A low value flags a mass
    RAGAS failure (API/credit outage, parse errors) rather than genuine low scores.
    Modes/metrics with zero records score 0.0 so a totally-missing mode is caught.
    """
    totals: dict[str, int] = {}
    valid: dict[str, int] = {}
    for rec in report.records:
        totals[rec.mode] = totals.get(rec.mode, 0) + 1
        for metric in EXPECTED_METRICS:
            if metric in rec.metrics:
                key = f"{rec.mode}_{metric}"
                valid[key] = valid.get(key, 0) + 1

    coverage: dict[str, float] = {}
    for mode in EXPECTED_MODES:
        denom = totals.get(mode, 0)
        for metric in EXPECTED_METRICS:
            key = f"{mode}_{metric}"
            coverage[key] = (valid.get(key, 0) / denom) if denom else 0.0
    return coverage


class EvalStage(Stage):
    name = "eval"
    milestone = "A-M5"
    requires = ("search",)

    def run(self, config: PipelineConfig) -> StageReport:
        if not config.knowledge_graph_path.exists():
            return self.skipped("no knowledge_graph.json (build the graph first)")
        if not config.allow_network:
            return self.skipped(
                "network gated; pass --allow-network or set GRAPHRAG_ALLOW_NETWORK=1"
            )
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return self.skipped(
                "ANTHROPIC_API_KEY not set (search answers + RAGAS judge both run on Claude)"
            )

        # 1) ensure question set exists
        if not config.eval_dataset_path.exists():
            log.info("generating %d synthetic questions...", DEFAULT_N)
            questions = _generate_questions(config, DEFAULT_N)
            if not questions:
                return self.failed("question generation produced 0 items")
            write_json(config.eval_dataset_path, questions)
            log.info("saved %d questions -> %s", len(questions), config.eval_dataset_path)

        # 2) skip if already evaluated (unless --force)
        if config.eval_report_path.exists() and not config.force:
            return self.skipped(
                f"{config.eval_report_path.name} exists (use --force to re-evaluate)"
            )

        # 3) full evaluation
        report = evaluate_baseline(config)

        # Refuse to write a contaminated baseline. If RAGAS scored too few
        # questions for any mode/metric (mass judge failure — API outage, credit
        # exhaustion, parse errors), fail honestly and leave report.json untouched
        # rather than reporting `ok` over a biased handful of survivors.
        coverage = _metric_coverage(report)
        weak = {k: v for k, v in coverage.items() if v < MIN_METRIC_COVERAGE}
        if weak:
            detail = ", ".join(f"{k}={v:.0%}" for k, v in sorted(weak.items()))
            return self.failed(
                f"RAGAS coverage below {MIN_METRIC_COVERAGE:.0%} for: {detail} "
                "— not writing report.json (likely an API/credit failure mid-run; "
                "fix credits and re-run with --force)"
            )

        write_json(config.eval_report_path, report)
        agg_short = {k: round(v, 3) for k, v in report.aggregate.items()}
        return self.ok(
            outputs=(config.eval_report_path,),
            n=report.n,
            coverage_min=round(min(coverage.values()), 2),
            **agg_short,
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from core.pipeline import PipelineRunner
    PipelineRunner([EvalStage()]).run(PipelineConfig.from_env())


if __name__ == "__main__":
    main()
