# From GraphRAG to Agentic RAG, Honestly Measured

*A 100-paper experiment on whether an agentic loop actually beats a GraphRAG baseline — and how to read the numbers without fooling yourself.*

📄 [Read the full paper (PDF)](https://github.com/parkjongmin-ddam/graphrag-paper/blob/main/docs/paper.pdf) · 💻 [Code on GitHub](https://github.com/parkjongmin-ddam/graphrag-paper) · 📝 [Markdown report](https://github.com/parkjongmin-ddam/graphrag-paper/blob/main/docs/PAPER.md)

Most papers on Agentic RAG show big numbers. I wanted to know how much of that holds when you build one carefully on a frozen baseline, run the same questions through both, and look hard at *why* the numbers move. So I built **GraphRAG** end-to-end on a 100-paper RAG-literature corpus, layered an **agentic loop** on top of it, and asked the same 40 questions through both. This post is the readable version.

## What's in the box

**Phase A — GraphRAG (the baseline).** Pull 100 RAG papers via Semantic Scholar forward-citations. Have Claude extract an entity/relation graph against a typed schema (Method, Model, Dataset, Metric, Task, Author, Institution, Paper + 7 relation types), run Leiden community detection on the relations, summarize each large community with an LLM. Two retrieval modes: *global* (concatenate community summaries → answer) and *local* (substring-match seed entities → 1-hop subgraph → corpus excerpts → answer). One LLM call per question, deterministic, **frozen** so the baseline never moves.

**Phase B — Agentic RAG (the loop).** A LangGraph DAG over the frozen retrievers:

```
START → route → search → grade ─┬─ sufficient ───────────→ reflect ─┬─ END
                                └─ insufficient → rewrite →         │
                                                  escalate ─────────┘
                                                                    │
                                                  hallucinated → regenerate → END
```

A third retriever — dense passage retrieval over chunked papers — is added, with a **cross-encoder reranker** (B-M6) doing retrieve-24 → rerank → top-8 on every vector query. Each conditional branch is a *single bounded retry*: no loops, no death spirals. Each LLM call has a fail-safe default (grader → "sufficient" on parse error; reflector → "grounded" on parse error) so a flaky judge cannot break the pipeline.

## What's the answer?

On 100 papers / 40 questions / Claude judge, agent vs. the *better* of the two baseline modes:

![Main result](https://raw.githubusercontent.com/parkjongmin-ddam/graphrag-paper/main/docs/figures/fig1-main-results.png)

| Metric | Baseline (best) | Agent | Δ |
|---|---|---|---|
| Faithfulness | 0.853 | 0.872 | +0.019 |
| Answer relevancy | 0.299 | **0.875** | **+0.576** |
| Context recall | 0.208 | **0.854** | **+0.646** |
| Context precision | 0.200 | **0.887** | **+0.687** |

Three of four metrics jump by 0.58–0.69. Faithfulness barely moves because both systems already ground their answers honestly — the difference isn't *whether* the LLM hallucinates, it's *whether the right context was retrieved at all*. That last clause is the whole story.

The headline holds when the corpus is scaled from 50 to 100 papers; routing is stable (the agent sends 32/40 questions to the vector route, 7 to local, 1 to global); the rerank step alone contributes most of the answer-relevancy gain (+0.084 over no-rerank), at a small ~0.025 cost in context recall — the textbook retrieve+rerank trade-off.

## The interesting part: why baseline answer relevancy is 0.30

A reviewer's first question, fair enough. The metric scores hedged answers like "the provided summaries do not contain that information" as **0**, no matter how faithful they are. Decomposing the baseline:

![Hedging](https://raw.githubusercontent.com/parkjongmin-ddam/graphrag-paper/main/docs/figures/fig4-hedging-decomposition.png)

- **Global** mode hedges in **28/40** answers. Mean answer relevancy: 0.033.
- **Local** hedges in **25/40**. The 15 *direct* local answers score **0.610**.
- Baseline **faithfulness stays at 0.853** — the hedges are *honest*, not hallucinated.

This matters because it changes what the result *means*. The low scores are not a metric artifact: community summaries and 1-hop subgraphs genuinely do not contain the specific numbers and parameters fact-specific questions ask for, and the model correctly declines. The agent's passage retrieval (and the reranker) fixes exactly that. The improvement is real and fair.

*But* the *size* of the answer-relevancy gap (+0.576) is partly amplified by the noncommittal-→-0 penalty. So if you're going to defend one number to a skeptic, defend **context recall (+0.646)** and **context precision (+0.687)** — those measure retrieval directly, are independent of answer phrasing, and don't carry the hedging penalty. Answer relevancy is corroborating, with the caveat stated.

This is the most useful thing I learned: in any RAG eval that uses RAGAS-style noncommittal detection, *report the noncommittal rate alongside answer relevancy*. Without it, you can't tell if your system is better or your baseline is just more polite.

## The methodological lesson nobody puts in the paper

Halfway through scaling 50 → 100 papers, half of them were contributing **zero** entities to the graph. Why? `MAX_TOKENS=2000` on the extractor. On full-text papers (intro + related work), the entity/relation JSON output ran past 2000 tokens, got truncated mid-array, failed to parse, and silently returned `[]`. The pipeline reported "ok"; the graph was half-empty.

Raising the cap to 8000 cut failures from ~50% to ~1% and grew the graph from 503/532 (50p, broken) to 1,342/1,489 (100p, fixed). It also means the 50→100 comparison conflates two changes (more papers *plus* a bug fix), which I flag in the report rather than hide.

The general lesson: for any LLM-as-structured-extractor, **validate parse-success rate**, not just that the pipeline ran end-to-end. A silent zero is worse than a loud error.

## Cross-checking with a second judge

A common worry with LLM-as-judge: the judge shares a family with the model under test. To check, I held the answers and contexts fixed and re-scored everything with **OpenAI gpt-4o-mini** (different family entirely). All four metrics keep their sign — *agent ≫ baseline* is judge-robust. Answer relevancy is the most consistent across judges (Δ +0.576 vs +0.544 — ~5% spread). Context-metric magnitudes shrink under OpenAI because it's more generous to the baseline's retrieval, but the agent advantage stays large (+0.45 recall, +0.32 precision). Notably, OpenAI rates the agent *higher* than Claude does on context metrics and faithfulness — no Claude self-preference on the agent side. Detail and per-metric numbers in §6.2 of the paper; reproduce via `python -m eval.judge_ablation`.

## What I'd do next

- **Human-authored question subset** to control for synthetic-question convenience.
- **Larger reranker** (`BAAI/bge-reranker-base`, 1 GB) — would test whether the precision/recall trade-off shifts at higher rerank capacity.
- Probably *not* "more agentic loops" — adding more retries/reflection rounds hit diminishing returns fast in earlier milestones; one bounded retry per conditional is the sweet spot.

## Run it yourself

```bash
git clone https://github.com/parkjongmin-ddam/graphrag-paper && cd graphrag-paper
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # or use a .env file
python run_pipeline.py --list
python run_pipeline.py --only agent_eval --allow-network --force
```

Or read the [Markdown report](https://github.com/parkjongmin-ddam/graphrag-paper/blob/main/docs/PAPER.md) / [compiled PDF](https://github.com/parkjongmin-ddam/graphrag-paper/blob/main/docs/paper.pdf). All 7 figures regenerate deterministically from the eval JSON via `python docs/figures/make_figures.py`.

---

*Code, paper, and eval artifacts: <https://github.com/parkjongmin-ddam/graphrag-paper>. MIT licensed. Issues and PRs welcome.*

*Draft refined with AI assistance; the experiments, code, and analysis are my own.*

---

## Publishing notes (for the author, remove before posting)

The image links above use absolute GitHub raw URLs, so this Markdown is **ready to paste into dev.to, Medium, LinkedIn, or any platform that accepts external images**. No further editing needed for image paths.

**dev.to** — paste the body into a new post. Recommended frontmatter at the very top:
```yaml
---
title: From GraphRAG to Agentic RAG, Honestly Measured
published: false
description: A 100-paper experiment on whether an agentic RAG loop actually beats a GraphRAG baseline — read the numbers without fooling yourself.
tags: rag, llm, langchain, machinelearning
cover_image: https://raw.githubusercontent.com/parkjongmin-ddam/graphrag-paper/main/docs/figures/fig1-main-results.png
---
```
Set `published: true` when ready.

**Medium** — paste the body. Medium auto-imports the H1 as the title. After pasting, replace the title block with their built-in title field. Cover image: drag-drop `fig1-main-results.png` (downloaded from the repo) at the top.

**LinkedIn Articles** — paste the body. LinkedIn doesn't render Markdown tables — replace the two tables with bullet summaries, or screenshot them.

**Personal Jekyll/Hugo/MDX blog** — copy as-is, swap image URLs to your own asset paths if you self-host figures.

After publishing, add the post URL near the top of `README.md` (e.g., `**Blog post**: <url>`) and remove this Publishing-notes section from the published copy.
