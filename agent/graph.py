"""
GraphRAG-Paper - B-M1 - agent/graph.py
--------------------------------------------------
The Phase B agent graph. B-M1 is the linear backbone:

    START -> route -> search -> END

`route` picks a retrieval mode (global/local/vector); `search` dispatches to the
matching retriever and produces the grounded answer. B-M2..M4 extend THIS graph
with conditional edges (grade -> re-retrieve / rewrite, reflect -> retry).

Note: Phase A's engine.search and the vector_search path each retrieve AND answer
in one call, so B-M1 keeps answering inside the `search` node. When B-M2 needs to
re-answer after grading, the answer step splits into its own node then.

`config` is injected via a closure (build_graph factory) rather than carried in
the state, keeping AgentState a pure data contract.
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from agent.grade import grade_node
from agent.reflect import reflect_node, regenerate_node
from agent.rewrite import rewrite_node
from agent.router import DEFAULT_ROUTE, route_node
from agent.state import AgentState
from core.config import PipelineConfig
from core.schemas import SearchResult

log = logging.getLogger("agent")

ESCALATE_K = 16  # wider vector retrieval when grading judges the context insufficient


def _search_node(config: PipelineConfig):
    """Build the dispatch node, closing over config."""

    def search_node(state: AgentState) -> dict:
        from search.engine import search          # frozen Phase A global/local
        from search.vector import vector_search   # B-M1 dense passage retrieval

        query = state["query"]
        route = state.get("route", DEFAULT_ROUTE)
        result = (
            vector_search(query, config) if route == "vector"
            else search(query, config, mode=route)
        )
        return {
            "answer": result.answer,
            "contexts": result.contexts,
            "sources": result.sources,
        }

    return search_node


def _escalate_node(config: PipelineConfig):
    """Build the re-retrieval node: wider vector search, closing over config."""

    def escalate(state: AgentState) -> dict:
        from search.vector import vector_search

        query = state.get("rewritten_query") or state["query"]  # B-M3: prefer rewrite
        result = vector_search(query, config, k=ESCALATE_K)
        log.info("escalate: re-retrieved via wider vector (k=%d) q=%r", ESCALATE_K, query[:50])
        return {
            "answer": result.answer,
            "contexts": result.contexts,
            "sources": result.sources,
            "route": "vector",   # the final answer is now vector-based
            "escalated": True,
        }

    return escalate


def _route_after_grade(state: AgentState) -> str:
    """Conditional edge: escalate once when grading found the context lacking."""
    if not state.get("sufficient", True) and not state.get("escalated", False):
        return "escalate"
    return "end"


def _route_after_reflect(state: AgentState) -> str:
    """Conditional edge: regenerate once ONLY on hallucination (grounded=False).

    Incompleteness is deliberately NOT a trigger: regenerating for completeness
    over-hedged answers and regressed answer_relevancy (RAGAS noncommittal), so
    reflection acts purely as a hallucination safety net.
    """
    if not state.get("grounded", True) and not state.get("reflected", False):
        return "regenerate"
    return "end"


def build_graph(config: PipelineConfig):
    """Compile the agent graph: route -> search -> grade -> (escalate?) -> END."""
    builder = StateGraph(AgentState)
    builder.add_node("route", route_node)
    builder.add_node("search", _search_node(config))
    builder.add_node("grade", grade_node)          # B-M2
    builder.add_node("rewrite", rewrite_node)      # B-M3
    builder.add_node("escalate", _escalate_node(config))  # B-M2
    builder.add_node("reflect", reflect_node)      # B-M4
    builder.add_node("regenerate", regenerate_node)  # B-M4
    builder.add_edge(START, "route")
    builder.add_edge("route", "search")
    builder.add_edge("search", "grade")
    builder.add_conditional_edges(
        "grade", _route_after_grade, {"escalate": "rewrite", "end": "reflect"}
    )
    builder.add_edge("rewrite", "escalate")        # B-M3: rewrite -> wider vector
    builder.add_edge("escalate", "reflect")        # B-M4: reflect on both paths
    builder.add_conditional_edges(
        "reflect", _route_after_reflect, {"regenerate": "regenerate", "end": END}
    )
    builder.add_edge("regenerate", END)
    return builder.compile()


def run_agent(query: str, config: PipelineConfig) -> SearchResult:
    """Run the agent end-to-end; returns a SearchResult (drop-in for search())."""
    final = build_graph(config).invoke({"query": query})
    route = final.get("route", DEFAULT_ROUTE)
    log.info("agent: route=%s sources=%d", route, len(final.get("sources", ())))
    return SearchResult(
        query=query,
        mode=route,
        answer=final.get("answer", ""),
        contexts=tuple(final.get("contexts", ())),
        sources=tuple(final.get("sources", ())),
    )


__all__ = ["build_graph", "run_agent"]
