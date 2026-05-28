"""
GraphRAG-Paper - paper figures
--------------------------------------------------
Generate the report/paper figures directly from the eval JSON artifacts so the
plots always match the data. Reads data/eval/*.json, writes docs/figures/*.png.

Run from the project root:  python docs/figures/make_figures.py
"""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
EVAL = ROOT / "data" / "eval"
OUT = Path(__file__).resolve().parent

METRICS = ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]
LABELS = ["Faithfulness", "Answer\nRelevancy", "Context\nRecall", "Context\nPrecision"]
C_BASE = "#9aa7b5"
C_AGENT = "#2f6fec"

# Honest hedging/noncommittal detector (same families as the fairness check).
HEDGE = re.compile(
    r"(don't have|do not have|cannot|can't|no (information|answer|details|mention)|"
    r"not (provide|contain|mention|specified|available|enough)|insufficient|unable to|"
    r"does not (specify|mention|provide|contain)|no specific|context does not|"
    r"provided (context|summaries|passages) do)",
    re.I,
)


def _agg(name: str) -> dict:
    return json.loads((EVAL / name).read_text(encoding="utf-8"))["aggregate"]


def _records(name: str) -> list[dict]:
    return json.loads((EVAL / name).read_text(encoding="utf-8"))["records"]


def _baseline_best(agg: dict, metric: str) -> float:
    vals = [agg.get(f"global_{metric}"), agg.get(f"local_{metric}")]
    vals = [v for v in vals if v is not None]
    return max(vals) if vals else 0.0


def fig_main_results() -> None:
    """Grouped bars: baseline_best vs agent across the 4 RAGAS metrics (100p, n=40)."""
    b = _agg("baseline_phaseA.json")
    a = _agg("report_phaseB.json")
    base = [_baseline_best(b, m) for m in METRICS]
    agent = [a.get(f"agent_{m}", 0.0) for m in METRICS]

    x = range(len(METRICS))
    w = 0.38
    fig, ax = plt.subplots(figsize=(8, 4.6))
    bars_b = ax.bar([i - w / 2 for i in x], base, w, label="Phase A baseline (best of global/local)", color=C_BASE)
    bars_a = ax.bar([i + w / 2 for i in x], agent, w, label="Phase B agent", color=C_AGENT)
    for bars in (bars_b, bars_a):
        for r in bars:
            ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.015,
                    f"{r.get_height():.3f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(LABELS)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("RAGAS score")
    ax.set_title("Phase B agent vs Phase A baseline (100-paper corpus, n=40, Claude judge)")
    ax.legend(loc="upper center", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "fig1-main-results.png", dpi=150)
    plt.close(fig)


def fig_scale_robustness() -> None:
    """Agent vs baseline_best at 50 and 100 papers — the headline holds at scale."""
    b50, a50 = _agg("baseline_phaseA_50p.json"), _agg("report_phaseB_50p.json")
    b100, a100 = _agg("baseline_phaseA.json"), _agg("report_phaseB.json")
    series = {
        "Baseline 50p": [_baseline_best(b50, m) for m in METRICS],
        "Agent 50p": [a50.get(f"agent_{m}", 0.0) for m in METRICS],
        "Baseline 100p": [_baseline_best(b100, m) for m in METRICS],
        "Agent 100p": [a100.get(f"agent_{m}", 0.0) for m in METRICS],
    }
    colors = ["#cdd5de", "#7aa0e8", C_BASE, C_AGENT]
    x = range(len(METRICS))
    w = 0.2
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for i, (label, vals) in enumerate(series.items()):
        ax.bar([xi + (i - 1.5) * w for xi in x], vals, w, label=label, color=colors[i])
    ax.set_xticks(list(x))
    ax.set_xticklabels(LABELS)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("RAGAS score")
    ax.set_title("Scale robustness: agent advantage persists from 50 to 100 papers (n=40)")
    ax.legend(loc="upper left", ncol=2, fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "fig2-scale-robustness.png", dpi=150)
    plt.close(fig)


def fig_routes() -> None:
    """Agent route distribution at 100p."""
    from collections import Counter

    def dist(name: str) -> Counter:
        return Counter(r["mode"] for r in _records(name))

    d100 = dist("report_phaseB.json")
    order = ["vector", "local", "global"]
    vals = [d100.get(k, 0) for k in order]
    fig, ax = plt.subplots(figsize=(6, 4.2))
    colors = [C_AGENT, "#67b26f", "#e0a24b"]
    bars = ax.bar(order, vals, color=colors, width=0.6)
    for r in bars:
        ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.4,
                str(int(r.get_height())), ha="center", va="bottom", fontsize=11)
    ax.set_ylabel("questions (of 40)")
    ax.set_title("Agent route distribution (100-paper corpus, n=40)")
    ax.set_ylim(0, max(vals) + 4)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "fig3-route-distribution.png", dpi=150)
    plt.close(fig)


def fig_hedging() -> None:
    """Fairness decomposition: baseline hedged vs non-hedged answer_relevancy."""
    recs = _records("baseline_phaseA.json")
    groups = {}
    for mode in ("global", "local"):
        mr = [r for r in recs if r["mode"] == mode and "answer_relevancy" in r["metrics"]]
        hed = [r["metrics"]["answer_relevancy"] for r in mr if HEDGE.search(r["answer"] or "")]
        noh = [r["metrics"]["answer_relevancy"] for r in mr if not HEDGE.search(r["answer"] or "")]
        groups[mode] = (
            statistics.mean(hed) if hed else 0.0, len(hed),
            statistics.mean(noh) if noh else 0.0, len(noh),
        )
    modes = list(groups)
    hed_means = [groups[m][0] for m in modes]
    noh_means = [groups[m][2] for m in modes]
    x = range(len(modes))
    w = 0.38
    fig, ax = plt.subplots(figsize=(6.5, 4.4))
    b1 = ax.bar([i - w / 2 for i in x], hed_means, w, label="hedged / noncommittal answers", color="#d98b8b")
    b2 = ax.bar([i + w / 2 for i in x], noh_means, w, label="direct answers", color="#67b26f")
    for m, bars in zip(("hed", "noh"), (b1, b2)):
        for i, r in enumerate(bars):
            n = groups[modes[i]][1] if m == "hed" else groups[modes[i]][3]
            ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.01,
                    f"{r.get_height():.2f}\n(n={n})", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(list(x))
    ax.set_xticklabels([m + " mode" for m in modes])
    ax.set_ylim(0, 0.8)
    ax.set_ylabel("mean answer_relevancy")
    ax.set_title("Why baseline answer_relevancy is low: hedging, not a metric artifact")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "fig4-hedging-decomposition.png", dpi=150)
    plt.close(fig)


def fig_rerank_ablation() -> None:
    """Cumulative: baseline -> agent (no rerank) -> agent + rerank (B-M6)."""
    b = _agg("baseline_phaseA.json")
    norr = _agg("report_phaseB_norerank_100p.json")
    rr = _agg("report_phaseB.json")
    base = [_baseline_best(b, m) for m in METRICS]
    no_rr = [norr.get(f"agent_{m}", 0.0) for m in METRICS]
    with_rr = [rr.get(f"agent_{m}", 0.0) for m in METRICS]

    x = range(len(METRICS))
    w = 0.27
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.bar([i - w for i in x], base, w, label="Phase A baseline (best)", color=C_BASE)
    ax.bar(list(x), no_rr, w, label="Phase B agent (no rerank)", color="#7aa0e8")
    ax.bar([i + w for i in x], with_rr, w, label="Phase B agent + rerank (B-M6)", color=C_AGENT)
    for xi, vals in zip(x, zip(base, no_rr, with_rr)):
        for offset, v in zip((-w, 0, w), vals):
            ax.text(xi + offset, v + 0.013, f"{v:.3f}", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(list(x))
    ax.set_xticklabels(LABELS)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("RAGAS score")
    ax.set_title("Cumulative improvements: baseline → agent → + cross-encoder rerank (100p, n=40)")
    ax.legend(loc="upper center", fontsize=8, ncol=3)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "fig5-rerank-ablation.png", dpi=150)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig_main_results()
    fig_scale_robustness()
    fig_routes()
    fig_hedging()
    fig_rerank_ablation()
    print("wrote figures to", OUT)
    for p in sorted(OUT.glob("*.png")):
        print(" -", p.name)


if __name__ == "__main__":
    main()
