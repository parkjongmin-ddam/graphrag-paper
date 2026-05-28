"""
GraphRAG-Paper - B-M3 - agent/rewrite.py
--------------------------------------------------
Query rewriting: when grading judges retrieval insufficient, rewrite the user's
question into a concise, retrieval-friendly query before the wider vector
re-retrieval. This sharpens recall on the escalation path (B-M2 escalated with
the raw question; B-M3 escalates with a query tuned for dense retrieval).

_rewrite (the LLM call) is isolated so the cleanup + fallback stay unit testable;
an empty rewrite falls back to the original query.
"""

from __future__ import annotations

import logging

from agent.state import AgentState

REWRITE_MODEL = "claude-haiku-4-5-20251001"
REWRITE_MAX_TOKENS = 120

REWRITE_PROMPT = """Rewrite the user's question into a concise search query optimized for dense passage retrieval over a corpus of retrieval-augmented generation (RAG) research papers.

Keep the key entities, methods, datasets, and numbers; drop conversational filler and question phrasing. Return ONLY the rewritten query — no prose, no quotes, no explanation."""

log = logging.getLogger("rewrite")


def _rewrite(query: str) -> str:
    """Ask Claude to rewrite the query for retrieval; return the raw response."""
    import anthropic

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=REWRITE_MODEL,
        max_tokens=REWRITE_MAX_TOKENS,
        system=REWRITE_PROMPT,
        messages=[{"role": "user", "content": query}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def rewrite_query(query: str) -> str:
    """Rewrite `query` for retrieval; fall back to the original if empty."""
    out = _rewrite(query).strip().strip('"').strip()
    if not out:
        log.warning("rewrite: empty output -> using original query")
        return query
    log.info("rewrite: %r -> %r", query[:50], out[:50])
    return out


def rewrite_node(state: AgentState) -> dict:
    """LangGraph node: produce a retrieval-friendly rewrite of the query."""
    return {"rewritten_query": rewrite_query(state["query"])}


__all__ = ["rewrite_query", "rewrite_node", "REWRITE_PROMPT"]
