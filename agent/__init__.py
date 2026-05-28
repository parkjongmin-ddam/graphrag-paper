"""Phase B agent — LangGraph orchestration over the Phase A search modes.

B-M1 wires an adaptive router (global / local / vector) as the first node;
B-M2..M4 add grading, query rewriting, and self-reflection as further nodes and
conditional edges on the same graph.
"""
