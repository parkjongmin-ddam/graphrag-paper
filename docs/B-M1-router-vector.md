# B-M1 — Adaptive Router + Vector Search (설계)

> Phase B의 첫 마일스톤. LLM 적응형 라우터가 쿼리마다 **global / local / vector**
> 중 하나를 고르고, 이를 **LangGraph 서브그래프**로 오케스트레이션한다. B-M2~M4는
> 같은 그래프에 노드/조건부 엣지로 얹는다.

## 1. 목표와 baseline 대비 공략점

Phase A baseline (`data/eval/baseline_phaseA.json`, n=20, Claude judge + fastembed):

| metric | global | local | 진단 |
|---|---|---|---|
| faithfulness | 0.843 | 0.736 | 양호 (환각 적음) |
| answer_relevancy | 0.095 | 0.048 | 대부분 noncommittal=0 (컨텍스트 부족→헷지) |
| context_recall | 0.025 | 0.050 | **핵심 약점** — 구체 사실이 컨텍스트에 없음 |
| context_precision | 0.050 | 0.000 | **핵심 약점** — 무관 컨텍스트 과투입 |

B-M1이 직접 겨냥하는 것:
- **벡터 검색**으로 *원문 패시지*를 끌어와 구체 수치 질문의 recall을 올린다
  (global은 추상 요약이라 수치가 없고, local은 엔티티명 substring 매칭이라 취약).
- **라우터**로 질문 유형에 맞는 모드를 골라 무관 컨텍스트 투입을 줄여 precision을 올린다.
- recall/precision이 오르면 모델이 헷지할 이유가 줄어 answer_relevancy도 간접 상승.

## 2. 모듈 레이아웃

```
agent/                    # Phase B (LangGraph) — 신규
├── __init__.py
├── state.py              # AgentState (TypedDict): 그래프 공유 상태
├── router.py             # LLM 적응형 라우터 노드 (global/local/vector)
├── graph.py              # LangGraph 와이어링: route -> retrieve -> answer
└── (이후) grade.py / rewrite.py / reflect.py   # B-M2~M4

search/
├── engine.py             # 기존 global/local (Phase A) — 그대로 동결
└── vector.py             # 신규: 벡터 인덱스 빌드 + 검색 (Chroma + fastembed)
```

**원칙:** Phase A의 `search/engine.py`는 비교 재현성을 위해 **변경하지 않는다.**
벡터 모드는 별도 모듈에 두고, 라우터가 양쪽(engine.search / vector.search)을 호출한다.

## 3. 벡터 검색 (`search/vector.py`)

**인덱스 빌드**
- 청킹: 각 코퍼스 문서의 `abstract / intro / related_work`를 ~1000자(약간 overlap)
  패시지로 분할.
- 임베딩: **fastembed `BAAI/bge-small-en-v1.5`**(로컬·무료·384d) 재사용.
- 저장: **Chroma**(영속, `data/vector/`), 메타데이터 `{paper_id, title, section, chunk_idx}`.
- 하네스 편입: `BuildVectorIndexStage`(milestone `B-M1`) 추가 — 코퍼스 존재 시 동작,
  인덱스 있으면 skip(`--force`로 재빌드). 기존 Stage 패턴(`core/stage.py`) 준수.

**검색**
- `vector_search(query, config, k=8) -> SearchResult`:
  쿼리 임베딩 → Chroma top-k → 패시지를 컨텍스트로, `paper_id`를 sources로 채워
  기존 `SearchResult` 스키마 재사용 → LLM 답변(`_llm_answer` 재사용).

**의존성 주입:** Chroma에는 langchain `FastEmbedEmbeddings`를 임베딩 함수로 전달
(텔레메트리 이슈와 무관 — 그 버그는 RAGAS 경로에 국한).

## 4. 라우터 (`agent/router.py`)

- LLM(claude-haiku, 나머지 단계와 동일)으로 쿼리를 `{global, local, vector}` 중
  하나로 분류 + 짧은 근거를 구조화 JSON으로 반환.
- 정책(프롬프트 + few-shot):
  - `global` — 광범위/주제/landscape ("어떤 접근들이…", "전반적 트렌드")
  - `local` — 특정 엔티티 중심(메서드/모델/데이터셋 명시)
  - `vector` — 구체 사실·수치("몇 %?", "데이터셋 몇 개?", "압축률?")
- JSON 파싱 실패 시 결정적 폴백 → `vector`(범용 recall 최선), **로그로 정직 보고**.
- B-M1은 **단일 모드 선택**(baseline 비교 깔끔). fan-out/merge는 이후로 보류.

## 5. LangGraph 와이어링 (`agent/graph.py`)

```
AgentState = TypedDict(query, route, mode, contexts, sources, answer)

START -> route_node -> retrieve_node -> answer_node -> END
```
- `route_node`: 라우터 호출 → `state.route`
- `retrieve_node`: route에 따라 global/local/vector 디스패치 → contexts/sources
- `answer_node`: 기존 GLOBAL/LOCAL 프롬프트(또는 vector 전용 프롬프트)로 답변
- B-M1은 **선형**. 조건부 엣지(grade→재검색/rewrite, reflect 루프)는 B-M2+에서 추가.
- 진입점: `run_agent(query, config) -> SearchResult` (eval이 `search()`처럼 호출).

## 6. 평가 통합 (B-M5 비교 — 지금 배선)

- eval에 `mode="agent"` 경로 추가 → **동일 `questions.json` + 동일 Claude judge +
  fastembed**로 Phase B 채점 → `report_phaseB.json` 생성, `baseline_phaseA.json`과 비교.
- B-M1 단계에서 이미 "라우터+벡터 vs baseline" 개선분 측정 가능.
- noncommittal 비율을 별도 로깅해 answer_relevancy 0점의 원인(헷지 vs 진짜 무관)을 분해.

## 7. 의존성

추가: `langgraph`, `langchain-chroma`(+ `chromadb`).
재사용: `langchain-anthropic`, `fastembed`, `langchain-community`.

## 8. 빌드 순서 (task list)

1. `search/vector.py` + `BuildVectorIndexStage` (+ 테스트) — 인덱스 빌드/검색
2. `agent/state.py` + `agent/router.py` (+ 라우터 단위테스트, LLM mock)
3. `agent/graph.py` LangGraph 와이어링 (+ smoke test)
4. eval에 `mode="agent"` 배선 → baseline 대비 측정
5. `requirements.txt` + `README.md` 갱신

## 9. 리스크 / 메모

- **청킹 전략**이 recall/precision을 좌우 — 단순하게 시작 후 튜닝.
- **라우터 오분류** → 잘못된 모드. B-M2 grading에서 재라우팅/재검색으로 완화.
- **Phase A 코드 동결** 유지(공정 비교). 벡터/agent는 신규 경로로만.
- Chroma 임베딩은 로컬 fastembed라 **추가 API 비용 0**, LLM 비용은 라우터(1콜)+답변(1콜)/쿼리.
