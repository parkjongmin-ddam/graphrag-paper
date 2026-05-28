"""Shared state for the Phase B agent graph (B-M1+).

A LangGraph node receives the AgentState and returns a partial update the runtime
merges in. Keeping the schema here (stdlib typing only) lets the router, retrieve,
and answer nodes agree on the contract without importing langgraph.
"""

from __future__ import annotations

from typing import TypedDict

from core.schemas import SearchMode


class AgentState(TypedDict, total=False):
    """Flows through route -> retrieve -> answer (B-M1); extended in B-M2+."""

    query: str
    route: SearchMode          # router's chosen mode: global / local / vector
    rationale: str             # router's short reason (debug / telemetry)
    contexts: tuple[str, ...]  # retrieved context blocks
    sources: tuple[str, ...]   # paper_ids backing the answer
    answer: str                # final grounded answer
    # B-M2 grading + conditional re-retrieval
    sufficient: bool           # did grading judge the context sufficient?
    grade_rationale: str       # grader's short reason
    escalated: bool            # whether re-retrieval (wider vector) already fired
    # B-M3 query rewriting
    rewritten_query: str       # retrieval-friendly query used on escalation
    # B-M4 self-reflection
    grounded: bool             # is every claim supported by the context?
    complete: bool             # does the answer fully address the question?
    reflect_rationale: str     # reflector's short reason
    reflected: bool            # whether a regeneration already fired


__all__ = ["AgentState"]
