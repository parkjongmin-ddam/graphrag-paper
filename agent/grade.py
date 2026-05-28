"""
GraphRAG-Paper - B-M2 - agent/grade.py
--------------------------------------------------
LLM retrieval grading: judge whether the retrieved context is sufficient to
answer the question. This drives the agent graph's conditional re-retrieval — an
"insufficient" verdict escalates to a wider vector search.

The LLM call (_grade) is isolated so the parse + fallback logic stays unit
testable offline. On any unparseable output the grader fails safe to
`sufficient=True` (do NOT escalate on a parse error — avoids burning calls); an
empty context is treated as insufficient so a dry retrieval always escalates.
"""

from __future__ import annotations

import json
import logging
import re

from agent.state import AgentState

GRADE_MODEL = "claude-haiku-4-5-20251001"
GRADE_MAX_TOKENS = 300

GRADE_PROMPT = """You judge whether the provided context is sufficient to answer a question about retrieval-augmented generation (RAG) research.

"sufficient" means the context contains the specific facts needed to answer — the relevant method, number, dataset, or comparison — not merely related background.

Return ONLY a JSON object, no prose, no markdown fence:
{"sufficient": true|false, "rationale": "<one short clause>"}"""

log = logging.getLogger("grade")


def _grade(question: str, context: str) -> str:
    """Ask Claude to grade context sufficiency; return the raw text response."""
    import anthropic

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=GRADE_MODEL,
        max_tokens=GRADE_MAX_TOKENS,
        system=GRADE_PROMPT,
        messages=[{"role": "user", "content": f"Question: {question}\n\nContext:\n{context}"}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def _parse_grade(raw: str) -> tuple[bool, str]:
    """Parse the grader's JSON; fail safe to sufficient=True on any problem."""
    match = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            sufficient = data.get("sufficient")
            rationale = (data.get("rationale") or "").strip()
            if isinstance(sufficient, bool):
                return sufficient, rationale
        except (json.JSONDecodeError, AttributeError):
            pass
    log.warning("grade: unparseable output %r -> fail-safe sufficient=True", (raw or "")[:80])
    return True, "fallback: grader output unparseable"


def grade_context(question: str, contexts: tuple[str, ...]) -> tuple[bool, str]:
    """Grade whether `contexts` suffice to answer `question`."""
    context = "\n\n".join(contexts).strip()
    if not context:
        return False, "no context retrieved"
    return _parse_grade(_grade(question, context))


def grade_node(state: AgentState) -> dict:
    """LangGraph node: grade the retrieved context, write the verdict to state."""
    sufficient, rationale = grade_context(state["query"], tuple(state.get("contexts", ())))
    log.info("grade: sufficient=%s (%s)", sufficient, rationale)
    return {"sufficient": sufficient, "grade_rationale": rationale}


__all__ = ["grade_context", "grade_node", "GRADE_PROMPT"]
