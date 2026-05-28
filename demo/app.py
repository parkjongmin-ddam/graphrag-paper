"""
GraphRAG-Paper - demo/app.py
--------------------------------------------------
Minimal Streamlit demo: ask a question about retrieval-augmented generation
research and see which retriever the agent picks, the grounded answer, and the
sources it used.

Run from the project root:
    pip install -r demo/requirements.txt   # streamlit (assumes main deps installed)
    streamlit run demo/app.py

Prereqs (same as the pipeline):
  - ANTHROPIC_API_KEY in env or .env
  - data/graph/knowledge_graph.json + data/vector/ (run the pipeline first)
"""

from __future__ import annotations

import os

import streamlit as st

from core.config import PipelineConfig

st.set_page_config(page_title="GraphRAG → Agentic RAG demo", page_icon="🔎", layout="wide")

st.title("GraphRAG → Agentic RAG")
st.caption(
    "Ask a question about retrieval-augmented generation research. The agent picks a "
    "retriever (global / local / vector), grades the result, and self-reflects before "
    "answering. See [the paper](https://github.com/parkjongmin-ddam/graphrag-paper/blob/main/docs/PAPER.md) for details."
)


@st.cache_resource
def _config() -> PipelineConfig:
    return PipelineConfig.from_env()


cfg = _config()

# Prereq checks — fail fast with actionable messages rather than tracebacks.
missing: list[str] = []
if not os.environ.get("ANTHROPIC_API_KEY"):
    missing.append("`ANTHROPIC_API_KEY` is not set (router + grader + reflect + answer all use Claude).")
if not cfg.knowledge_graph_path.exists():
    missing.append(f"`{cfg.knowledge_graph_path}` is missing. Run the pipeline through `extract_graph` + `communities`.")
if not (cfg.vector_dir / "chroma.sqlite3").exists():
    missing.append(f"`{cfg.vector_dir}/` is empty. Run `python run_pipeline.py --only vector_index --force`.")
if missing:
    st.error("Prereqs not satisfied:")
    for m in missing:
        st.markdown(f"- {m}")
    st.stop()

# Example questions seeded from the eval set (concrete, fact-specific).
EXAMPLES = [
    "What compression rate does xRAG achieve and on which datasets?",
    "How does Self-RAG decide when to retrieve?",
    "What is the difference between global and local search in GraphRAG?",
    "Which reranker does the agent use after dense retrieval?",
]

with st.sidebar:
    st.subheader("Try an example")
    for ex in EXAMPLES:
        if st.button(ex, use_container_width=True):
            st.session_state["query"] = ex
    st.markdown("---")
    st.caption(
        "**Routes**\n\n"
        "- `global` — community summaries\n"
        "- `local`  — entity subgraph + corpus excerpts\n"
        "- `vector` — dense retrieval + cross-encoder rerank (B-M6)"
    )

query = st.text_input(
    "Your question",
    value=st.session_state.get("query", ""),
    placeholder="e.g. What compression rate does xRAG achieve?",
)

if st.button("Run agent", type="primary", disabled=not query.strip()):
    with st.spinner("Routing → searching → grading → (maybe rewrite/escalate) → reflecting…"):
        # Lazy import so the page loads quickly before the heavy deps initialize.
        from agent.graph import run_agent

        result = run_agent(query.strip(), cfg)

    col_route, col_sources = st.columns([1, 2])
    with col_route:
        st.metric("Route picked", result.mode)
    with col_sources:
        if result.sources:
            st.markdown("**Sources** (paper_id):")
            st.markdown(", ".join(f"`{s}`" for s in result.sources))
        else:
            st.markdown("**Sources**: _none_")

    st.markdown("### Answer")
    st.markdown(result.answer or "_(empty)_")

    if result.contexts:
        with st.expander(f"Show retrieved context ({len(result.contexts)} block(s))"):
            for i, ctx in enumerate(result.contexts, 1):
                st.markdown(f"**Block {i}**")
                st.text(ctx[:4000])
                if len(ctx) > 4000:
                    st.caption(f"… (truncated, {len(ctx)} chars total)")
