# graphrag-paper

[![Repo](https://img.shields.io/badge/GitHub-parkjongmin--ddam%2Fgraphrag--paper-181717?logo=github)](https://github.com/parkjongmin-ddam/graphrag-paper)
[![CI](https://img.shields.io/github/actions/workflow/status/parkjongmin-ddam/graphrag-paper/ci.yml?label=CI&logo=github)](https://github.com/parkjongmin-ddam/graphrag-paper/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Last commit](https://img.shields.io/github/last-commit/parkjongmin-ddam/graphrag-paper)](https://github.com/parkjongmin-ddam/graphrag-paper/commits/main)
[![Report](https://img.shields.io/badge/%F0%9F%93%84_report-docs%2FPAPER.md-2f6fec)](docs/PAPER.md)

RAG 논문 코퍼스 기반 **GraphRAG 구현 → Agentic RAG 결합** 프로젝트.
목표는 RAG / LangChain / LangGraph 실력 심화.

**저장소**: <https://github.com/parkjongmin-ddam/graphrag-paper>

## 구성 (2단계)

- **Phase A — GraphRAG**: entity/relationship 추출 → knowledge graph →
  community detection → global / local search (LangGraph 오케스트레이션)
- **Phase B — Agentic RAG**: A의 검색 서브그래프 위에 adaptive routing ·
  retrieval grading · query rewriting · self-reflection 루프를 얹음

A를 단방향으로 안정화하고 RAGAS baseline을 고정한 뒤 B를 얹어,
"agentic 루프가 baseline 대비 얼마나 개선했는가"를 정량 측정한다.

## 마일스톤

**Phase A**
- A-M0  코퍼스 수집 + 환경
- A-M1  entity / relationship 추출
- A-M2  그래프 구축 + community detection (Leiden)
- A-M3  community summary 생성
- A-M4  global / local search 구현
- A-M5  RAGAS baseline 확정

**Phase B**
- B-M1  LLM adaptive 라우터 (global / local / vector 선택)
- B-M2  retrieval grading + 조건부 재검색
- B-M3  query rewriting
- B-M4  self-reflection (hallucination / 완결성)
- B-M5  동일 평가셋으로 A 대비 개선분 측정

## 코퍼스 정책

- 주제: RAG 단일 주제 (entity 연결성 확보)
- 규모: 30~50편으로 검증 후 100편으로 확장 (단계적)
- 텍스트: abstract + intro + related work
- 섹션 추출: arXiv LaTeX source 우선, 실패 시 GROBID(PDF) 폴백
- entity 스키마(도메인 특화): Method, Model, Dataset, Metric, Task, Author, Institution, Paper
- relationship: USES, EVALUATED_ON, IMPROVES/OUTPERFORMS, COMBINES, PROPOSED_BY, CITES

## 하네스 (파이프라인 오케스트레이션)

전 단계를 하나의 **타입 안전 파이프라인**으로 묶는 스캐폴드. 각 마일스톤은
`Stage`로 구현되고, 공용 데이터 계약(`core/schemas.py`)을 입출력으로 주고받는다.
아직 구현 안 된 단계는 가짜 결과 대신 **정직하게 `stub`/`skipped`로 보고**하므로,
지금도 전체 파이프라인을 끝까지 실행해 "현재 어디까지 됐는지"를 한눈에 본다.

```
core/                  # 하네스 척추 (스테이지에 의존하지 않음)
├── schemas.py         # 단계 간 타입 계약 (frozen dataclass)
├── config.py          # PipelineConfig: 경로 + 토글(network/force/llm)
├── stage.py           # Stage 베이스 + StageReport + StageStatus
├── artifacts.py       # data/ JSON 읽기/쓰기
└── pipeline.py        # PipelineRunner: 순서 실행 + 요약 테이블
run_pipeline.py        # 조립 루트 + CLI (모든 스테이지를 여기서 와이어링)
```

**스테이지 상태**
- `ok` 실제 작업 수행 + 산출물 생성
- `stub` 도메인 로직 미구현 (의도적 placeholder, 가짜 데이터 없음)
- `skipped` 입력 없음 / 이미 최신
- `failed` 예상치 못한 오류 (runner가 잡아서 보고, 프로세스는 안 죽음)

## 폴더 구조

```
graphrag-paper/
├── core/             # 하네스 척추 (위 참조)
├── ingest/
│   ├── collect.py            # 시드 + forward citation 확장 + 스코어링
│   ├── extract_sections.py   # LaTeX 우선, GROBID 폴백           (A-M0)
│   └── build_corpus.py       # 정제 코퍼스 빌드                  (A-M0)
├── graph/
│   ├── extract.py            # entity/relation 추출             (A-M1)
│   └── communities.py        # Leiden + community summary       (A-M2/M3)
├── search/
│   ├── engine.py             # global / local search (Phase A, 동결)  (A-M4)
│   └── vector.py             # dense passage retrieval (Chroma+fastembed) (B-M1)
├── agent/            # Phase B — LangGraph 오케스트레이션
│   ├── state.py              # AgentState (그래프 공유 상태)
│   ├── router.py             # LLM 적응형 라우터 (global/local/vector)  (B-M1)
│   └── graph.py              # route -> search 그래프 + run_agent()    (B-M1)
├── eval/
│   ├── ragas_eval.py         # RAGAS baseline (Claude judge + fastembed) (A-M5)
│   └── agent_eval.py         # agent 채점 + baseline 대비 비교          (B-M1)
├── data/
│   ├── raw/         # arxiv 원본 (LaTeX source / PDF)
│   ├── corpus/      # 정제 논문 JSON
│   ├── graph/       # knowledge_graph.json
│   ├── vector/      # Chroma 벡터 인덱스 (B-M1)
│   └── eval/        # questions.json + baseline_phaseA.json + report_phaseB.json
├── docs/            # PAPER.md(전체 보고서) + paper.tex/references.bib + 설계 문서 + figures/
├── tests/           # 하네스 단위 테스트 (pytest)
└── run_pipeline.py  # 파이프라인 CLI
```

## 사용법

> 모듈 임포트(`core`) 때문에 **프로젝트 루트에서** 실행한다.

```bash
pip install -r requirements.txt

# 스테이지 목록
python run_pipeline.py --list

# 전체 파이프라인 (네트워크 호출은 기본 차단 → collect는 skipped)
python run_pipeline.py

# 구간 실행 / 단일 스테이지
python run_pipeline.py --from extract_sections --to build_corpus
python run_pipeline.py --only collect --allow-network --force

# 개별 스테이지 단독 실행 (스크립트 경로 아님, -m 모듈 모드)
python -m ingest.collect          # GRAPHRAG_ALLOW_NETWORK=1 필요
python -m ingest.extract_sections

# 테스트
python -m pytest -q
```

**환경 변수 / 게이트**
- `S2_API_KEY` — (선택) Semantic Scholar 키. 없으면 낮은 rate limit.
- `GRAPHRAG_ALLOW_NETWORK=1` 또는 `--allow-network` — collect의 라이브 호출 허용
  (실수로 네트워크/비용 발생하지 않도록 기본 차단).
- `GRAPHRAG_FORCE=1` 또는 `--force` — 산출물이 있어도 재빌드.
- `GRAPHRAG_LLM_MODEL` — graph/search/eval 단계의 LLM 모델 (기본 placeholder).

collect 튜닝(SEED_PAPERS / RAG_KEYWORDS / 가중치)은 `ingest/collect.py` 상단에서 조정한다.

## 진행 상태

**Phase A — 완료 (baseline 확정)**
- [x] A-M0  collect / extract_sections / build_corpus (코퍼스 50편 검증 후 **100편 확장**)
- [x] A-M1  entity/relationship 추출 → `data/graph/knowledge_graph.json`
- [x] A-M2/M3  community detection (Leiden) + summary
- [x] A-M4  global / local search
- [x] A-M5  RAGAS baseline → `data/eval/baseline_phaseA.json` (n=20)
- [x] 하네스  core/ 스캐폴드 + run_pipeline.py + tests (전 단계 end-to-end 실행 가능)

> RAGAS judge는 Claude(claude-haiku) + 로컬 fastembed 임베딩을 사용한다
> (OpenAI quota 이슈로 전환). eval 스테이지는 지표 커버리지가 낮으면 오염된
> report를 쓰지 않고 `failed`로 보고한다. 상세는 `eval/ragas_eval.py`.

**Phase B — 진행 중**
- [x] B-M1  adaptive 라우터(LLM, global/local/vector) + 벡터 검색(Chroma+fastembed)
  + LangGraph 오케스트레이션(`agent/`) + agent eval — 설계: `docs/B-M1-router-vector.md`
- [x] B-M2  retrieval grading + 조건부 재검색 (wider vector escalate) — 설계: `docs/B-M2-grading.md`
- [x] B-M3  query rewriting (escalation 시 검색 친화적 재작성 후 재검색)
- [x] B-M4  self-reflection (환각=grounded:false일 때만 재생성, 답변-우선 재작성)
- [x] B-M5  동일 평가셋(n=40)으로 A 대비 개선분 측정
- [x] B-M6  vector 라우트에 cross-encoder rerank (Xenova/ms-marco-MiniLM-L-12-v2,
  retrieve 24 → rerank → top 8) — 설계: `docs/B-M6-rerank.md`

> 📄 **전체 보고서**: [`docs/PAPER.md`](docs/PAPER.md) — 방법론 + 정량 결과 + 공정성 분석
> (영어 본문 + 한국어 초록, 그림 5개). 제출용 LaTeX: `docs/paper.tex` + `docs/references.bib`
> (Overleaf에서 XeLaTeX로 컴파일).
>
> 📝 **블로그 글**(읽기 쉬운 영문 요약): [`docs/BLOG.md`](docs/BLOG.md) — Medium·dev.to에 그대로 게시 가능
> · 🖥️ **인터랙티브 데모**: [`demo/app.py`](demo/app.py) (Streamlit) — `streamlit run demo/app.py`
> · 🚀 **외부 배포 가이드**: [`docs/DEPLOY.md`](docs/DEPLOY.md) — GitHub Topics · Overleaf PDF · arXiv · HF Spaces · 블로그 플랫폼별 절차

> **최종 결과 — 코퍼스 100편, n=40, 동일 judge (agent+rerank vs baseline_best):**
> - faithfulness     0.853 → **0.872**  (+0.019)
> - answer_relevancy 0.299 → **0.875**  (+0.576)
> - context_recall   0.208 → **0.854**  (+0.646)
> - context_precision 0.200 → **0.887**  (+0.687)
>
> agent route(n=40, w/ rerank): vector 32 / local 7 / global 1.  스냅샷: `*_100p.json`(100편),
> `report_phaseB_norerank_100p.json`(B-M5, 리랭커 전), `report_phaseB_rerank_100p.json`(B-M6, 현재),
> `*_50p.json`(50편), `*_n20.json`(n=20).
>
> **B-M5 → B-M6 rerank ablation** (no-rerank → +rerank): AR **+0.084**, CP **+0.025**,
> F 0.000, CR **-0.025** — 정밀도/관련성은 올라가고 recall은 미세 하락 (전형적인 retrieve+rerank
> trade-off). 답변 품질(answer_relevancy)이 가장 크게 개선됐다.
>
> **50→100 스케일 견고성**: 헤드라인(agent≫baseline)이 코퍼스 2배에서도 유지된다.
> context recall/precision delta는 오히려 **커졌고**(+0.637→+0.671, +0.600→+0.662),
> 코퍼스가 커질수록 Phase A global/local 검색이 상대적으로 더 약해지고 vector retrieval은
> 잘 확장됨을 시사한다. faithfulness delta 축소(+0.069→+0.019)는 baseline faithfulness가
> 원래 높아(~0.85) 차별점이 아니었기 때문. agent 절대값 소폭 하락(answer_relevancy
> 0.891→0.791)은 논문 2배로 distractor가 늘어난 자연스러운 효과.
>
> **주의 — 50→100은 순수 스케일 비교가 아님**: 50편 그래프는 `extract.py MAX_TOKENS=2000`로
> 빌드돼 일부 논문의 entity/relation JSON이 잘렸다(파싱 실패 → 그래프 기여 0). 100편 확장 시
> 이를 발견해 8000으로 올렸고(truncation 거의 제거: 실패 ~50%→1%), 그래프가 편당 더 조밀해졌다
> (503ent/532rel → 1342ent/1489rel). 따라서 50→100 증분에는 (논문 수 증가 + truncation 버그
> 수정)이 섞인다. 단, **동일 코퍼스 내 agent vs baseline은 양쪽이 같은 그래프를 쓰므로 깨끗하다.**
>
> **B-M4 주의**: 재생성을 incompleteness까지 발동하면 답변이 과도하게 헷지되어
> RAGAS noncommittal로 answer_relevancy가 후퇴(0.86→0.69)했다. 환각일 때만 발동 +
> 답변-우선 재작성으로 보수화. 스냅샷: `report_phaseB_m1~m3/m4hedged.json`.
