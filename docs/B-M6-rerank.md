# B-M6 — Cross-Encoder Rerank on the Vector Route (설계)

> B-M1의 vector route는 bi-encoder(BAAI/bge-small-en-v1.5)로 top-k=8 dense
> 검색만 했다. fact-specific 질문에서 *주제는 같지만 정답이 없는* 청크가 상위에
> 끼면 답변이 흐려진다. B-M6은 retrieve→**rerank** 패턴을 얹어 cross-encoder가
> (query, passage) 쌍에 공동으로 attention 하도록 한다 — 표준적인 RAG 다음 수.

## 그래프 변화

```
(이전 B-M5)  vector_retrieve(query, k=8)                 → 8 hits → LLM
(이후 B-M6)  vector_retrieve(query, k=24) → rerank → top 8 → LLM
```

LangGraph 노드는 추가되지 않는다 (rerank는 `vector_search` 내부에 캡슐화). 새
노드를 만들면 표면적은 늘지만 모든 vector 경로에서 항상 같이 돌아야 하므로
함수 내부 통합이 KISS.

## 모듈

- `search/rerank.py`
  - `RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-12-v2"` — 120MB, fastembed 로컬, **API 비용 0**
  - `_get_reranker()` — `@functools.lru_cache(maxsize=1)`로 프로세스 1회 다운로드/로드
  - `rerank_hits(query, hits, top_k)` — (query, hit['text']) 쌍별 cross-encoder
    스코어 → 내림차순 정렬 → 상위 top_k. **실패 시 입력 순서 truncated 반환**
    (모델 다운로드 일시 실패가 라이브 쿼리를 깨트리지 않게)
- `search/vector.py`
  - 새 상수 `RERANK_POOL_MULT = 3`
  - `vector_search(..., rerank: bool = True)` — `rerank=True`면 `k * 3` 후보를
    뽑아 rerank → top k. `rerank=False`는 pre-B-M6 동작(ablation/회귀 용)

## 설계 결정

- **Bi-encoder는 그대로 유지** — chroma 인덱스(B-M1)는 변경 없음. rerank는
  bi-encoder가 좁혀준 후보 위에서만 도는 게 비용·품질 모두 최적.
- **Pool 배수 3x** — 표준 비율. 8→24(일반), 16→48(escalate). pool을 더 키워도
  top 후보 안에 정답이 들어 있을 확률은 한계 효용이 빠르게 줄고, rerank latency만 증가.
- **B-M2 escalate 자동 수혜** — `_escalate_node`도 `vector_search(k=16)`을 부른다.
  rerank 기본값이 True라 escalate도 48→16 rerank로 자동 강화 (코드 수정 불필요).
- **Phase A 동결 유지** — Phase A는 vector를 안 쓰므로 baseline은 변동 없음.
  agent vs baseline 비교가 깨끗하게 유지된다.
- **Fail-safe** — 모델 로드/스코어링 어떤 단계에서든 예외가 나면 입력 순서로
  fallback + 로그. Grade/Reflect의 fail-safe 패턴과 동일 철학.

## 측정

`run_agent`가 새 `vector_search`를 쓰므로 `agent_eval --force` 재실행이 곧 B-M6
측정이다. 재실행 전 B-M5 결과(`report_phaseB.json`)를 `report_phaseB_norerank_100p.json`로
스냅샷해 **with-rerank vs no-rerank** 비교를 그대로 보관한다. baseline
(`baseline_phaseA.json`)은 그대로 동결.

기대: **context_precision 가장 큰 개선** (rerank가 정확히 노리는 지표),
**context_recall은 같거나 살짝 상승**(같은 후보 풀에서 더 좋은 top-k 선택),
**answer_relevancy 상승**(더 정확한 컨텍스트 → 더 직접적인 답변),
**faithfulness 영향 미미**(이미 0.87 수준).

## 빌드 순서

1. `search/rerank.py` (LRU 캐시 + fail-safe)
2. `search/vector.py` — `RERANK_POOL_MULT` + `vector_search(rerank=True)`
3. `tests/test_harness.py` — `rerank_hits` 정렬·fallback 단위 테스트 + 통합 점검 (오프라인 mock)
4. `report_phaseB.json` → `report_phaseB_norerank_100p.json` 스냅샷
5. `agent_eval --force` 재측정
6. README + `docs/PAPER.md` 결과 갱신
