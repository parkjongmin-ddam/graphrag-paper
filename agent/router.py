"""
GraphRAG-Paper - B-M1 - agent/router.py
--------------------------------------------------
LLM adaptive router: classify a query into one of the three retrieval modes the
agent can run, so fact-specific questions reach the right retriever instead of
always hitting global community summaries (the Phase A baseline's weakness).

  - global : broad / thematic / landscape questions  -> community summaries
  - local  : entity-centric questions (named method/model/dataset) -> subgraph
  - vector : specific factual / quantitative questions -> dense passage retrieval

The LLM call (_classify) is isolated so the parse + fallback logic stays unit
testable offline. On any unparseable / invalid output the router falls back to
`vector` (the most generally useful retriever) and says so honestly in the log.
"""

from __future__ import annotations

import json
import logging
import re

from agent.state import AgentState
from core.schemas import SearchMode

# ----------------------------- constants -----------------------------
ROUTER_MODEL = "claude-haiku-4-5-20251001"
ROUTER_MAX_TOKENS = 300
VALID_ROUTES: tuple[SearchMode, ...] = ("global", "local", "vector")
DEFAULT_ROUTE: SearchMode = "vector"

ROUTER_PROMPT = """You route a question about retrieval-augmented generation (RAG) research to ONE retrieval mode over a knowledge base of RAG papers.

Modes:
- "global": broad, thematic, or survey-style questions about trends, categories, or the overall landscape ("what approaches improve RAG?", "how has RAG evolved?").
- "local": questions centered on a specific named entity — a method, model, dataset, or metric — and its relationships ("what does REPLUG use?", "how does ColBERT relate to DPR?").
- "vector": specific factual or quantitative questions whose answer is a concrete detail in some paper — a number, score, rate, count, or precise mechanism ("what compression rate does xRAG achieve?", "how many datasets does MMEB include?").

Return ONLY a JSON object, no prose, no markdown fence:
{"route": "global|local|vector", "rationale": "<one short clause>"}"""

log = logging.getLogger("router")


def _classify(query: str) -> str:
    """Ask Claude to classify the query; return the raw text response."""
    import anthropic

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=ROUTER_MODEL,
        max_tokens=ROUTER_MAX_TOKENS,
        system=ROUTER_PROMPT,
        messages=[{"role": "user", "content": query}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def _parse_route(raw: str) -> tuple[SearchMode, str]:
    """Parse the router's JSON; fall back to DEFAULT_ROUTE on any problem."""
    match = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            route = (data.get("route") or "").strip().lower()
            rationale = (data.get("rationale") or "").strip()
            if route in VALID_ROUTES:
                return route, rationale  # type: ignore[return-value]
        except (json.JSONDecodeError, AttributeError):
            pass
    log.warning(
        "router: unparseable/invalid output %r -> default %s", (raw or "")[:80], DEFAULT_ROUTE
    )
    return DEFAULT_ROUTE, "fallback: router output unparseable"


def route_query(query: str) -> tuple[SearchMode, str]:
    """Classify `query` into a retrieval mode; returns (route, rationale)."""
    route, rationale = _parse_route(_classify(query))
    log.info("route=%s for %r (%s)", route, query[:60], rationale)
    return route, rationale


def route_node(state: AgentState) -> dict:
    """LangGraph node: read state['query'], write the chosen route + rationale."""
    route, rationale = route_query(state["query"])
    return {"route": route, "rationale": rationale}


__all__ = ["route_query", "route_node", "ROUTER_PROMPT", "DEFAULT_ROUTE", "VALID_ROUTES"]
