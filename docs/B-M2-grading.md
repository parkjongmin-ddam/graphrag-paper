# B-M2 — Retrieval Grading + Conditional Re-retrieval (설계)

> B-M1의 `route → search` 그래프에 **grading**과 **조건부 재검색**을 얹어, 라우터
> 오분류나 부실 검색을 한 번 보정한다. query rewriting(B-M3)·self-reflection(B-M4)은
> 이후 같은 그래프에 더 얹는다.

## 그래프

```
START → route → search → grade → ┬─ (sufficient)            ──────────→ END
                                  └─ (insufficient & !escalated) → escalate → END
```

- **grade**: LLM이 질문 대비 현재 컨텍스트의 충분성을 판정 → `{sufficient, rationale}`.
- **조건부 엣지** `_route_after_grade(state)`:
  - `not sufficient and not escalated` → `"escalate"`
  - 그 외 → `END`  (단일 바운드 재시도, 루프 없음)
- **escalate**: `vector_search(query, config, k=ESCALATE_K)` 로 재검색·재답변하고
  `escalated=True` 설정 → END. global/local 라우팅이 부실하면 vector로 전환,
  vector였으면 k를 넓혀(기본 8 → 16) 재검색.

## 노드 / 모듈

- `agent/grade.py`
  - `grade_context(question, contexts) -> (sufficient: bool, rationale: str)` — LLM 호출(`_grade`)
    + 순수 파서(`_parse_grade`). 파싱 실패 시 **fail-safe `sufficient=True`**(불필요한
    재검색·비용 방지), 로그로 보고.
  - `grade_node(state) -> dict` — `{sufficient, grade_rationale}`
  - `escalate_node(config)` 클로저 → `escalate(state) -> dict` (`vector_search` 재검색)
- `agent/state.py` — `sufficient: bool`, `grade_rationale: str`, `escalated: bool` 추가
- `agent/graph.py` — grade/escalate 노드 + 조건부 엣지로 재배선

## 설계 결정

- **재검색 = wider vector escalate** — 모든 라우트에 일률 유효하고, query rewriting과
  역할이 겹치지 않는다(rewriting은 B-M3). 단일 재시도로 비용·복잡도 억제.
- **Phase A engine 동결 유지** — grade는 `search`가 낸 `SearchResult.contexts`를 본다.
  escalate가 fire할 때만 첫 답변 1회를 폐기(insufficient인 소수 케이스).
- **fail-safe 기본값** — grader 출력 불량 시 escalate하지 않음(보수적). 정직하게 로그.

## 측정

`run_agent`가 새 그래프를 쓰므로 `agent_eval --force` 재실행이 곧 B-M2 측정이다.
재실행 전 B-M1 결과(`report_phaseB.json`)를 `report_phaseB_m1.json`로 스냅샷해
B-M1 → B-M2 증분도 비교한다. baseline은 `baseline_phaseA.json`로 그대로 보존.

기대: B-M1이 이미 높아(0.66~0.92) 증분은 제한적이며, 주 효과는 **global/local로
오라우팅된 소수 질문의 보정**(robustness)과 context precision 소폭 상승.

## 빌드 순서

1. `agent/state.py` 필드 추가
2. `agent/grade.py` (grade + escalate) + 단위테스트(파싱·노드·조건부, 오프라인 mock)
3. `agent/graph.py` 재배선 + run_agent escalation 경로 테스트
4. `agent_eval --force` 재측정 (B-M1 스냅샷 후)
