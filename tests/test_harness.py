"""Tests for the pipeline harness spine (config, artifacts, stages, runner)."""

from __future__ import annotations

import json

from core.artifacts import load_paper_list, write_records
from core.config import PipelineConfig
from core.schemas import PaperRef
from core.stage import StageStatus
from run_pipeline import build_runner

EXPECTED_ORDER = [
    "collect", "extract_sections", "build_corpus",
    "extract_graph", "communities", "search", "eval",
    "vector_index", "agent_eval",
]


def test_config_derives_paths(tmp_path):
    cfg = PipelineConfig.from_env(root=tmp_path)
    assert cfg.paper_list_path == tmp_path / "data" / "paper_list.json"
    assert cfg.knowledge_graph_path == tmp_path / "data" / "graph" / "knowledge_graph.json"
    cfg.ensure_dirs()
    assert cfg.corpus_dir.is_dir() and cfg.eval_dir.is_dir()


def test_paper_ref_roundtrip(tmp_path):
    cfg = PipelineConfig.from_env(root=tmp_path)
    cfg.ensure_dirs()
    refs = [
        PaperRef("p1", "2005.11401", "RAG", "abstract", 2020, 1000, 0.9, ("CS",)),
        PaperRef("p2", "2007.01282", "FiD", "abstract", 2020, 500, 0.7, ()),
    ]
    write_records(cfg.paper_list_path, refs)
    assert load_paper_list(cfg) == refs


def test_runner_orders_stages():
    assert build_runner().stage_names() == EXPECTED_ORDER


def test_full_run_is_honest_without_data(tmp_path):
    # No artifacts + network gated -> all skipped, nothing FAILED.
    cfg = PipelineConfig.from_env(root=tmp_path)
    reports = build_runner().run(cfg)
    assert [r.stage for r in reports] == EXPECTED_ORDER
    assert all(r.status is not StageStatus.FAILED for r in reports)
    statuses = {r.stage: r.status for r in reports}
    assert statuses["collect"] is StageStatus.SKIPPED  # network gated
    assert statuses["eval"] is StageStatus.SKIPPED      # no eval set


def test_extract_sections_stage_gates_on_network(tmp_path):
    # With paper_list present but network gated, the stage must refuse live arXiv
    # calls (mirrors the collect stage's gating policy).
    from ingest.extract_sections import ExtractSectionsStage

    cfg = PipelineConfig.from_env(root=tmp_path)
    cfg.ensure_dirs()
    write_records(cfg.paper_list_path, [PaperRef("p1", "2005.11401", "RAG", "a", 2020, 10, 0.5, ())])
    report = ExtractSectionsStage().run(cfg)
    assert report.status is StageStatus.SKIPPED
    assert "network" in report.detail.lower()


def test_split_sections_extracts_intro_and_related():
    from ingest.extract_sections import split_sections

    latex = (
        r"\documentclass{article}" "\n"
        r"\begin{document}" "\n"
        r"\section{Introduction}" "\n"
        "We propose a new RAG method.\n"
        r"\section{Related Work}" "\n"
        "Prior work covered dense retrieval.\n"
        r"\section{Method}" "\n"
        "Our pipeline starts here.\n"
        r"\end{document}"
    )
    secs = split_sections(latex)
    assert "We propose" in secs["intro"]
    assert "Prior work" in secs["related_work"]
    assert "Our pipeline" not in secs.get("related_work", "")


def test_latex_to_text_strips_commands():
    from ingest.extract_sections import latex_to_text

    text = latex_to_text(r"We use BERT \cite{Devlin2018} with embedding dim $d=768$.")
    assert "BERT" in text
    assert "Devlin2018" not in text
    assert "\\cite" not in text


def test_build_corpus_joins_metadata_and_cleans_text(tmp_path):
    from ingest.build_corpus import BuildCorpusStage

    cfg = PipelineConfig.from_env(root=tmp_path)
    cfg.ensure_dirs()
    write_records(
        cfg.paper_list_path,
        [PaperRef("p1", "2005.11401", "RAG", "abstract from S2", 2020, 100, 0.9, (), ("ref_a", "ref_b"))],
    )
    raw_payload = {
        "arxiv_id": "2005.11401",
        "abstract": "Pre-trained models store knowledge.",
        "intro": "We propose RAG.",
        "related_work": "REALM <cit.> and ORQA <cit.>.",
        "source": "latex",
    }
    (cfg.raw_dir / "2005.11401.json").write_text(
        json.dumps(raw_payload, ensure_ascii=False), encoding="utf-8"
    )

    report = BuildCorpusStage().run(cfg)
    assert report.status is StageStatus.OK
    out = json.loads((cfg.corpus_dir / "p1.json").read_text(encoding="utf-8"))
    assert out["paper_id"] == "p1"
    assert out["arxiv_id"] == "2005.11401"
    assert out["title"] == "RAG"
    assert "We propose RAG" in out["intro"]
    assert "[cite]" in out["related_work"]
    assert "<cit.>" not in out["related_work"]
    assert out["citations"] == ["ref_a", "ref_b"]


def test_extract_graph_parser_roundtrip():
    from graph.extract import _parse_llm

    raw = '''Here is the extraction:
{"entities": [{"name": "BERT", "type": "Model", "description": "encoder"},
              {"name": "Lewis et al.", "type": "Author", "description": "authors"}],
 "relations": [{"source": "RAG", "target": "BERT", "type": "USES", "description": ""}]}
'''
    ents, rels = _parse_llm(raw)
    assert {e["name"] for e in ents} == {"BERT", "Lewis et al."}
    assert rels[0]["type"] == "USES"


def test_extract_graph_stage_gates_on_network(tmp_path):
    from graph.extract import ExtractGraphStage

    cfg = PipelineConfig.from_env(root=tmp_path)
    cfg.ensure_dirs()
    (cfg.corpus_dir / "p1.json").write_text(
        json.dumps(
            {
                "paper_id": "p1",
                "abstract": "a",
                "intro": "",
                "related_work": "",
                "citations": [],
            }
        ),
        encoding="utf-8",
    )
    report = ExtractGraphStage().run(cfg)
    assert report.status is StageStatus.SKIPPED
    assert "network" in report.detail.lower()


def test_detect_communities_separates_disjoint_clusters(tmp_path):
    from graph.communities import detect_communities

    cfg = PipelineConfig.from_env(root=tmp_path)
    cfg.ensure_dirs()
    # Two disjoint triangles: {a,b,c} and {x,y,z}
    kg = {
        "entities": [{"id": eid, "type": "Method", "name": eid} for eid in "abcxyz"],
        "relations": [
            {"source_id": "a", "target_id": "b", "type": "USES"},
            {"source_id": "b", "target_id": "c", "type": "USES"},
            {"source_id": "c", "target_id": "a", "type": "USES"},
            {"source_id": "x", "target_id": "y", "type": "USES"},
            {"source_id": "y", "target_id": "z", "type": "USES"},
            {"source_id": "z", "target_id": "x", "type": "USES"},
        ],
        "communities": [],
    }
    cfg.knowledge_graph_path.write_text(json.dumps(kg), encoding="utf-8")
    comms = detect_communities(cfg)
    groups = [set(c.entity_ids) for c in comms]
    assert {"a", "b", "c"} in groups
    assert {"x", "y", "z"} in groups


def test_find_seeds_matches_entity_names_in_query():
    from search.engine import _find_seeds

    entities = [
        {"id": "Model:bert", "name": "BERT", "type": "Model"},
        {"id": "Method:dense_passage_retrieval", "name": "Dense Passage Retrieval", "type": "Method"},
        {"id": "Model:gpt", "name": "GPT", "type": "Model"},  # too short (3 chars)
        {"id": "Dataset:nq", "name": "Natural Questions", "type": "Dataset"},
    ]
    found = _find_seeds("How does Dense Passage Retrieval compare to BM25 on Natural Questions?", entities)
    names = {e["name"] for e in found}
    assert "Dense Passage Retrieval" in names
    assert "Natural Questions" in names
    assert "GPT" not in names  # filtered by len < 4
    assert "BERT" not in names  # not mentioned in query


def test_search_stage_gates_on_network(tmp_path):
    from search.engine import SearchStage

    cfg = PipelineConfig.from_env(root=tmp_path)
    cfg.ensure_dirs()
    cfg.knowledge_graph_path.write_text(
        json.dumps({"entities": [], "relations": [], "communities": []}),
        encoding="utf-8",
    )
    report = SearchStage().run(cfg)
    assert report.status is StageStatus.SKIPPED
    assert "network" in report.detail.lower()


def test_eval_stage_gates_on_anthropic_key(tmp_path, monkeypatch):
    # With network allowed but ANTHROPIC_API_KEY absent, EvalStage must SKIP cleanly
    # rather than crashing inside ragas / langchain_anthropic. The judge (and the
    # search answers it scores) both run on Claude now.
    from eval.ragas_eval import EvalStage

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = PipelineConfig.from_env(root=tmp_path, allow_network=True)
    cfg.ensure_dirs()
    cfg.knowledge_graph_path.write_text(
        json.dumps({"entities": [], "relations": [], "communities": []}),
        encoding="utf-8",
    )
    report = EvalStage().run(cfg)
    assert report.status is StageStatus.SKIPPED
    assert "anthropic" in report.detail.lower()


def test_only_selection_runs_single_stage(tmp_path):
    cfg = PipelineConfig.from_env(root=tmp_path)
    reports = build_runner().run(cfg, only=["search"])
    assert [r.stage for r in reports] == ["search"]
    assert reports[0].status is StageStatus.SKIPPED  # no knowledge graph yet


def test_metric_coverage_flags_partial_failure():
    # A run where `global` scored every metric but `local` produced nothing (the
    # exact mass-failure shape we hit when Claude credits ran out mid-run) must
    # surface as low coverage for local, so EvalStage can fail instead of writing
    # a contaminated report.json built from the surviving global records.
    from core.schemas import EvalRecord, EvalReport
    from eval.ragas_eval import EXPECTED_METRICS, MIN_METRIC_COVERAGE, _metric_coverage

    records = []
    for i in range(5):
        records.append(EvalRecord(
            question=f"q{i}", answer="a", mode="global", contexts=("c",),
            ground_truth="g", metrics={m: 1.0 for m in EXPECTED_METRICS},
        ))
        records.append(EvalRecord(
            question=f"q{i}", answer="a", mode="local", contexts=("c",),
            ground_truth="g", metrics={},  # local: every metric dropped (failed)
        ))
    report = EvalReport(dataset="x.json", n=5, aggregate={}, records=tuple(records))

    coverage = _metric_coverage(report)
    assert all(coverage[f"global_{m}"] == 1.0 for m in EXPECTED_METRICS)
    assert all(coverage[f"local_{m}"] == 0.0 for m in EXPECTED_METRICS)
    weak = {k: v for k, v in coverage.items() if v < MIN_METRIC_COVERAGE}
    assert weak and all(k.startswith("local_") for k in weak)


# ----------------------------- B-M1 vector search -----------------------------
def test_chunk_doc_splits_sections():
    # Each non-empty section is chunked with metadata; empty sections produce
    # nothing; chunks stay within the size bound.
    from search.vector import CHUNK_CHARS, _chunk_doc

    doc = {
        "paper_id": "p1", "title": "T",
        "abstract": "a" * 1500,   # -> 2 chunks (overlap window)
        "intro": "i" * 500,       # -> 1 chunk
        "related_work": "",       # -> skipped
    }
    chunks = _chunk_doc(doc)
    sections = [meta["section"] for _, meta in chunks]
    assert "abstract" in sections and "intro" in sections
    assert "related_work" not in sections          # empty section skipped
    assert all(meta["paper_id"] == "p1" for _, meta in chunks)
    assert all(len(text) <= CHUNK_CHARS for text, _ in chunks)
    assert sections.count("abstract") == 2


def test_vector_index_stage_skips_without_corpus(tmp_path):
    from search.vector import BuildVectorIndexStage

    cfg = PipelineConfig.from_env(root=tmp_path)
    cfg.ensure_dirs()
    report = BuildVectorIndexStage().run(cfg)
    assert report.status is StageStatus.SKIPPED
    assert "corpus" in report.detail.lower()


def test_vector_index_build_and_retrieve(tmp_path):
    # Build a tiny index over two clearly distinct papers (offline: fastembed is
    # local) and confirm retrieval returns the topically-matching paper.
    from search.vector import _index_exists, build_index, vector_retrieve

    cfg = PipelineConfig.from_env(root=tmp_path)
    cfg.ensure_dirs()
    docs = [
        {"paper_id": "dpr1", "title": "Dense Passage Retrieval",
         "abstract": "Dense passage retrieval encodes queries and passages with a "
                     "dual encoder for open-domain question answering.",
         "intro": "", "related_work": ""},
        {"paper_id": "sum1", "title": "Text Summarization",
         "abstract": "Abstractive summarization generates concise summaries of long "
                     "documents using sequence to sequence models.",
         "intro": "", "related_work": ""},
    ]
    for d in docs:
        (cfg.corpus_dir / f"{d['paper_id']}.json").write_text(
            json.dumps(d), encoding="utf-8"
        )

    n = build_index(cfg)
    assert n >= 2
    assert _index_exists(cfg)

    hits = vector_retrieve("how does dense passage retrieval work?", cfg, k=1)
    assert hits and hits[0]["paper_id"] == "dpr1"


# ----------------------------- B-M1 adaptive router -----------------------------
def test_parse_route_valid():
    from agent.router import _parse_route

    route, rationale = _parse_route('{"route": "vector", "rationale": "specific number"}')
    assert route == "vector"
    assert rationale == "specific number"


def test_parse_route_handles_fence_and_invalid():
    from agent.router import DEFAULT_ROUTE, _parse_route

    # JSON wrapped in prose + a markdown fence still parses
    fenced = 'My choice:\n```json\n{"route": "local", "rationale": "entity-centric"}\n```'
    assert _parse_route(fenced)[0] == "local"
    # unknown route falls back to the default
    assert _parse_route('{"route": "banana"}')[0] == DEFAULT_ROUTE
    # non-JSON falls back to the default
    assert _parse_route("no json here")[0] == DEFAULT_ROUTE


def test_route_query_uses_classified_route(monkeypatch):
    # route_query parses whatever the LLM returns; mock the LLM call so the test
    # is offline and deterministic.
    from agent import router

    monkeypatch.setattr(
        router, "_classify",
        lambda q: '{"route": "global", "rationale": "broad thematic question"}',
    )
    route, rationale = router.route_query("What are the main approaches to RAG?")
    assert route == "global"
    assert "broad" in rationale


def test_route_node_updates_state(monkeypatch):
    from agent import router

    monkeypatch.setattr(router, "_classify", lambda q: '{"route": "vector", "rationale": "num"}')
    update = router.route_node({"query": "How many datasets does MMEB include?"})
    assert update["route"] == "vector"
    assert "rationale" in update


# ----------------------------- B-M1 agent graph (LangGraph) -----------------------------
def test_run_agent_vector_route(tmp_path, monkeypatch):
    # route -> vector dispatches vector_search and surfaces its result. LLM calls
    # (router + search) are mocked so the graph wiring is tested offline.
    from agent import grade, graph, reflect, router
    import search.vector as vec
    from core.schemas import SearchResult

    monkeypatch.setattr(router, "_classify", lambda q: '{"route": "vector", "rationale": "num"}')
    monkeypatch.setattr(grade, "_grade", lambda q, c: '{"sufficient": true, "rationale": "ok"}')
    monkeypatch.setattr(reflect, "_reflect",
                        lambda q, a, c: '{"grounded": true, "complete": true, "rationale": "ok"}')
    monkeypatch.setattr(
        vec, "vector_search",
        lambda q, cfg, k=8: SearchResult(
            query=q, mode="vector", answer="VANS", contexts=("vc",), sources=("p1",)
        ),
    )
    cfg = PipelineConfig.from_env(root=tmp_path)
    result = graph.run_agent("How many datasets does MMEB include?", cfg)
    assert result.mode == "vector"
    assert result.answer == "VANS"
    assert result.sources == ("p1",)


def test_run_agent_global_route_dispatches_engine(tmp_path, monkeypatch):
    # route -> global dispatches the frozen Phase A engine.search with mode=global.
    from agent import grade, graph, reflect, router
    import search.engine as eng
    from core.schemas import SearchResult

    monkeypatch.setattr(router, "_classify", lambda q: '{"route": "global", "rationale": "broad"}')
    monkeypatch.setattr(grade, "_grade", lambda q, c: '{"sufficient": true, "rationale": "ok"}')
    monkeypatch.setattr(reflect, "_reflect",
                        lambda q, a, c: '{"grounded": true, "complete": true, "rationale": "ok"}')
    captured: dict = {}

    def fake_search(q, cfg, mode="global"):
        captured["mode"] = mode
        return SearchResult(query=q, mode=mode, answer="GANS", contexts=("gc",), sources=())

    monkeypatch.setattr(eng, "search", fake_search)
    cfg = PipelineConfig.from_env(root=tmp_path)
    result = graph.run_agent("What approaches improve RAG?", cfg)
    assert result.mode == "global"
    assert captured["mode"] == "global"
    assert result.answer == "GANS"


# ----------------------------- B-M1 agent eval vs baseline -----------------------------
def test_agent_coverage_counts_valid_per_metric():
    from core.schemas import EvalRecord
    from eval.agent_eval import _agent_coverage
    from eval.ragas_eval import EXPECTED_METRICS

    recs = [
        EvalRecord(question="q1", answer="a", mode="vector",
                   metrics={m: 1.0 for m in EXPECTED_METRICS}),
        EvalRecord(question="q2", answer="a", mode="global",
                   metrics={"faithfulness": 1.0}),  # other metrics dropped (failed)
    ]
    cov = _agent_coverage(recs)
    assert cov["faithfulness"] == 1.0        # 2/2
    assert cov["answer_relevancy"] == 0.5    # 1/2


def test_compare_phase_a_b(tmp_path):
    from eval.agent_eval import compare_phase_a_b

    cfg = PipelineConfig.from_env(root=tmp_path)
    cfg.ensure_dirs()
    cfg.baseline_report_path.write_text(json.dumps({"aggregate": {
        "global_faithfulness": 0.80, "local_faithfulness": 0.70,
        "global_context_recall": 0.02, "local_context_recall": 0.05,
    }}), encoding="utf-8")
    cfg.phaseB_report_path.write_text(json.dumps({"aggregate": {
        "agent_faithfulness": 0.85, "agent_context_recall": 0.40,
    }}), encoding="utf-8")

    rows = {r["metric"]: r for r in compare_phase_a_b(cfg)}
    assert rows["faithfulness"]["b_agent"] == 0.85
    assert rows["faithfulness"]["a_best"] == 0.80      # max(global, local)
    assert round(rows["context_recall"]["delta"], 2) == 0.35  # 0.40 - max(0.02, 0.05)


def test_agent_eval_stage_skips_without_graph(tmp_path):
    from eval.agent_eval import AgentEvalStage

    cfg = PipelineConfig.from_env(root=tmp_path, allow_network=True)
    cfg.ensure_dirs()
    report = AgentEvalStage().run(cfg)
    assert report.status is StageStatus.SKIPPED


# ----------------------------- B-M2 grading + conditional re-retrieval -----------------------------
def test_parse_grade_valid_and_failsafe():
    from agent.grade import _parse_grade

    assert _parse_grade('{"sufficient": false, "rationale": "missing numbers"}') == (
        False, "missing numbers",
    )
    assert _parse_grade('ok:\n```json\n{"sufficient": true, "rationale": "has it"}\n```')[0] is True
    # unparseable -> fail-safe sufficient=True (do NOT escalate on a parse failure)
    assert _parse_grade("not json")[0] is True


def test_grade_node_updates_state(monkeypatch):
    from agent import grade

    monkeypatch.setattr(grade, "_grade", lambda q, c: '{"sufficient": false, "rationale": "thin"}')
    update = grade.grade_node({"query": "q", "contexts": ("c1",)})
    assert update["sufficient"] is False
    assert "grade_rationale" in update


def test_route_after_grade_conditional():
    from agent.graph import _route_after_grade

    assert _route_after_grade({"sufficient": False, "escalated": False}) == "escalate"
    assert _route_after_grade({"sufficient": True, "escalated": False}) == "end"
    assert _route_after_grade({"sufficient": False, "escalated": True}) == "end"  # already retried


def test_run_agent_escalates_with_rewritten_query(tmp_path, monkeypatch):
    # route=global, grading judges the context thin -> rewrite the query, then
    # escalate to wider vector USING THE REWRITTEN query (B-M3).
    from agent import grade, graph, reflect, rewrite, router
    import search.engine as eng
    import search.vector as vec
    from core.schemas import SearchResult

    monkeypatch.setattr(router, "_classify", lambda q: '{"route": "global", "rationale": "broad"}')
    monkeypatch.setattr(
        eng, "search",
        lambda q, cfg, mode="global": SearchResult(
            query=q, mode=mode, answer="A1", contexts=("thin",), sources=()
        ),
    )
    monkeypatch.setattr(grade, "_grade", lambda q, c: '{"sufficient": false, "rationale": "thin"}')
    monkeypatch.setattr(rewrite, "_rewrite", lambda q: "rewritten dense query")
    monkeypatch.setattr(reflect, "_reflect",
                        lambda q, a, c: '{"grounded": true, "complete": true, "rationale": "ok"}')
    captured: dict = {}

    def fake_vector(q, cfg, k=8):
        captured["q"] = q
        return SearchResult(query=q, mode="vector", answer="ESC", contexts=("rich",), sources=("p9",))

    monkeypatch.setattr(vec, "vector_search", fake_vector)
    cfg = PipelineConfig.from_env(root=tmp_path)
    result = graph.run_agent("What rate does X achieve?", cfg)
    assert result.answer == "ESC"
    assert result.mode == "vector"
    assert result.sources == ("p9",)
    assert captured["q"] == "rewritten dense query"   # escalate used the rewritten query


# ----------------------------- B-M3 query rewriting -----------------------------
def test_rewrite_query_cleans_and_falls_back(monkeypatch):
    from agent import rewrite

    monkeypatch.setattr(rewrite, "_rewrite", lambda q: '  "better dense query"  ')
    assert rewrite.rewrite_query("orig") == "better dense query"   # trimmed + dequoted
    monkeypatch.setattr(rewrite, "_rewrite", lambda q: "   ")
    assert rewrite.rewrite_query("orig") == "orig"                 # empty -> fall back


def test_rewrite_node_updates_state(monkeypatch):
    from agent import rewrite

    monkeypatch.setattr(rewrite, "_rewrite", lambda q: "rw query")
    update = rewrite.rewrite_node({"query": "original question"})
    assert update["rewritten_query"] == "rw query"


# ----------------------------- B-M4 self-reflection -----------------------------
def test_parse_reflection_valid_and_failsafe():
    from agent.reflect import _parse_reflection

    g, c, r = _parse_reflection('{"grounded": false, "complete": true, "rationale": "x"}')
    assert g is False and c is True and r == "x"
    fenced = '```json\n{"grounded": true, "complete": false, "rationale": "y"}\n```'
    assert _parse_reflection(fenced)[1] is False
    # unparseable -> fail-safe grounded=complete=True (do NOT regenerate)
    g2, c2, _ = _parse_reflection("nope")
    assert g2 is True and c2 is True


def test_reflect_node_updates_state(monkeypatch):
    from agent import reflect

    monkeypatch.setattr(
        reflect, "_reflect",
        lambda q, a, c: '{"grounded": true, "complete": false, "rationale": "missing detail"}',
    )
    update = reflect.reflect_node({"query": "q", "answer": "a", "contexts": ("c",)})
    assert update["grounded"] is True
    assert update["complete"] is False


def test_route_after_reflect():
    # B-M4 (conservative): regenerate ONLY on hallucination (grounded=False);
    # mere incompleteness does NOT trigger regeneration (over-hedging regressed
    # answer_relevancy), so self-reflection acts purely as a hallucination net.
    from agent.graph import _route_after_reflect

    assert _route_after_reflect({"grounded": False, "complete": True, "reflected": False}) == "regenerate"
    assert _route_after_reflect({"grounded": True, "complete": False, "reflected": False}) == "end"
    assert _route_after_reflect({"grounded": True, "complete": True, "reflected": False}) == "end"
    assert _route_after_reflect({"grounded": False, "complete": False, "reflected": True}) == "end"


def test_regenerate_node_updates_answer(monkeypatch):
    from agent import reflect

    monkeypatch.setattr(reflect, "_regenerate", lambda q, c, fb: "NEW ANSWER")
    update = reflect.regenerate_node(
        {"query": "q", "contexts": ("c",), "reflect_rationale": "fix grounding"}
    )
    assert update["answer"] == "NEW ANSWER"
    assert update["reflected"] is True


def test_run_agent_regenerates_on_ungrounded(tmp_path, monkeypatch):
    # vector answer flagged ungrounded by reflection -> regenerate once.
    from agent import grade, graph, reflect, router
    import search.vector as vec
    from core.schemas import SearchResult

    monkeypatch.setattr(router, "_classify", lambda q: '{"route": "vector", "rationale": "num"}')
    monkeypatch.setattr(
        vec, "vector_search",
        lambda q, cfg, k=8: SearchResult(
            query=q, mode="vector", answer="ORIG", contexts=("c",), sources=("p1",)
        ),
    )
    monkeypatch.setattr(grade, "_grade", lambda q, c: '{"sufficient": true, "rationale": "ok"}')
    monkeypatch.setattr(
        reflect, "_reflect",
        lambda q, a, c: '{"grounded": false, "complete": true, "rationale": "unsupported claim"}',
    )
    monkeypatch.setattr(reflect, "_regenerate", lambda q, c, fb: "REVISED")
    cfg = PipelineConfig.from_env(root=tmp_path)
    result = graph.run_agent("q", cfg)
    assert result.answer == "REVISED"   # regenerated after ungrounded reflection
