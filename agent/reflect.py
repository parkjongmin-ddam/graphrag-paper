"""
GraphRAG-Paper - B-M4 - agent/reflect.py
--------------------------------------------------
Self-reflection: after the answer is produced, check it against the question and
its context for (1) grounded — every claim is supported by the context (no
invented facts); (2) complete — it actually answers the question. If either
fails, regenerate the answer ONCE (bounded) from the same context with a
stricter, feedback-aware prompt. This is the hallucination safety net; it does
not re-retrieve (that is B-M2/B-M3's job).

_reflect and _regenerate (the LLM calls) are isolated so the parse + state logic
stays unit testable. On unparseable reflection it fails safe to
grounded=complete=True (no regeneration).
"""

from __future__ import annotations

import json
import logging
import re

from agent.state import AgentState

REFLECT_MODEL = "claude-haiku-4-5-20251001"
REFLECT_MAX_TOKENS = 300
REGEN_MAX_TOKENS = 800

REFLECT_PROMPT = """You review a draft answer to a question about retrieval-augmented generation (RAG) research against the context it was built from.

Judge two things:
- "grounded": every factual claim in the answer is supported by the context (no invented facts or numbers).
- "complete": the answer actually addresses what the question asked.

Return ONLY a JSON object, no prose, no markdown fence:
{"grounded": true|false, "complete": true|false, "rationale": "<one short clause>"}"""

REGEN_PROMPT = """You revise a draft answer about RAG research so it is grounded in the provided context.

Remove any claim the context does not support, but otherwise answer the question DIRECTLY and CONFIDENTLY using the facts that ARE in the context — cite specific methods, datasets, and numbers. Do NOT add hedging or "the context does not mention" disclaimers unless the context truly contains nothing relevant. Lead with the answer, not caveats."""

log = logging.getLogger("reflect")


def _reflect(question: str, answer: str, context: str) -> str:
    """Ask Claude to judge grounding + completeness; return the raw response."""
    import anthropic

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=REFLECT_MODEL,
        max_tokens=REFLECT_MAX_TOKENS,
        system=REFLECT_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Question: {question}\n\nDraft answer:\n{answer}\n\nContext:\n{context}",
        }],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def _regenerate(question: str, context: str, feedback: str) -> str:
    """Ask Claude to revise the answer given reviewer feedback; return the text."""
    import anthropic

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=REFLECT_MODEL,
        max_tokens=REGEN_MAX_TOKENS,
        system=REGEN_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Question: {question}\n\nReviewer feedback: {feedback}\n\nContext:\n{context}",
        }],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def _parse_reflection(raw: str) -> tuple[bool, bool, str]:
    """Parse the reflector's JSON; fail safe to grounded=complete=True on problems."""
    match = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            grounded = data.get("grounded")
            complete = data.get("complete")
            rationale = (data.get("rationale") or "").strip()
            if isinstance(grounded, bool) and isinstance(complete, bool):
                return grounded, complete, rationale
        except (json.JSONDecodeError, AttributeError):
            pass
    log.warning(
        "reflect: unparseable output %r -> fail-safe grounded=complete=True", (raw or "")[:80]
    )
    return True, True, "fallback: reflection output unparseable"


def reflect_answer(question: str, answer: str, contexts: tuple[str, ...]) -> tuple[bool, bool, str]:
    """Reflect on whether `answer` is grounded in `contexts` and complete."""
    if not (answer or "").strip():
        return False, False, "empty answer"
    context = "\n\n".join(contexts).strip()
    return _parse_reflection(_reflect(question, answer, context))


def reflect_node(state: AgentState) -> dict:
    """LangGraph node: reflect on the current answer, write the verdict to state."""
    grounded, complete, rationale = reflect_answer(
        state["query"], state.get("answer", ""), tuple(state.get("contexts", ()))
    )
    log.info("reflect: grounded=%s complete=%s (%s)", grounded, complete, rationale)
    return {"grounded": grounded, "complete": complete, "reflect_rationale": rationale}


def regenerate_node(state: AgentState) -> dict:
    """LangGraph node: revise the answer from the same context, feedback-aware."""
    context = "\n\n".join(state.get("contexts", ())).strip()
    answer = _regenerate(state["query"], context, state.get("reflect_rationale", ""))
    log.info("regenerate: revised answer (%d chars)", len(answer))
    return {"answer": answer, "reflected": True}


__all__ = ["reflect_answer", "reflect_node", "regenerate_node", "REFLECT_PROMPT", "REGEN_PROMPT"]
