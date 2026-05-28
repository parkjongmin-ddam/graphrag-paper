# GraphRAG에서 Agentic RAG로, 정직하게 측정해보기

*RAG 논문 100편 코퍼스에서 agentic loop가 GraphRAG baseline을 정말로 이기는지, 그리고 그 숫자를 *자기 자신*을 속이지 않고 읽는 법.*

📄 [논문 PDF](https://github.com/parkjongmin-ddam/graphrag-paper/blob/main/docs/paper.pdf) · 💻 [GitHub 코드](https://github.com/parkjongmin-ddam/graphrag-paper) · 📝 [Markdown 리포트](https://github.com/parkjongmin-ddam/graphrag-paper/blob/main/docs/PAPER.md)

요즘 Agentic RAG 논문들은 큰 숫자를 보여줍니다. 저는 그게 *baseline을 고정하고, 같은 질문을 양쪽에 던지고, 숫자가 왜 움직였는지를 진지하게 들여다봤을 때도* 얼마나 살아남는지 알고 싶었습니다. 그래서 RAG 논문 100편을 코퍼스로 **GraphRAG**를 처음부터 직접 구현하고, 그 위에 **agentic loop**를 얹은 뒤, 같은 40개 질문을 양쪽에 던졌습니다. 이 글은 그 결과의 읽기 쉬운 버전입니다.

## 무엇을 만들었나

**Phase A — GraphRAG (baseline).** Semantic Scholar의 forward citation으로 RAG 논문 100편을 모읍니다. Claude가 도메인 스키마(Method, Model, Dataset, Metric, Task, Author, Institution, Paper + 7가지 relation)에 맞춰 엔티티/관계 그래프를 추출하고, Leiden community detection을 돌린 뒤 큰 community마다 LLM으로 요약을 생성합니다. 두 가지 검색 모드: *global*(community summary들을 concatenate해서 답변), *local*(쿼리에서 substring으로 seed 엔티티를 찾고 1-hop subgraph로 확장 → 논문 발췌문과 함께 답변). 질문당 LLM 호출 한 번. 결정론적이고, **고정**(frozen)되어 있어 baseline이 움직이지 않습니다.

**Phase B — Agentic RAG (loop).** Phase A의 (고정된) 검색기 위에 LangGraph DAG를 얹습니다:

```
START → route → search → grade ─┬─ sufficient ───────────→ reflect ─┬─ END
                                └─ insufficient → rewrite →         │
                                                  escalate ─────────┘
                                                                    │
                                                  hallucinated → regenerate → END
```

세 번째 검색기 — chunk 단위 dense passage retrieval — 가 추가됩니다. 모든 vector 질의는 **cross-encoder reranker**(B-M6)를 거쳐 retrieve-24 → rerank → top-8 패턴으로 동작합니다. 각 조건부 분기는 *bounded single retry*: 루프나 무한 재시도 없음. LLM 호출마다 fail-safe 기본값(grader는 파싱 실패 시 "sufficient", reflector는 "grounded")이 있어, 한 번 흔들리는 judge가 파이프라인 전체를 깨트리지 못합니다.

## 결과는?

100편 코퍼스, 40개 질문, Claude judge 기준 — agent vs *둘 중 더 나은* baseline 모드:

![Main result](https://raw.githubusercontent.com/parkjongmin-ddam/graphrag-paper/main/docs/figures/fig1-main-results.png)

| Metric | Baseline (best) | Agent | Δ |
|---|---|---|---|
| Faithfulness | 0.853 | 0.872 | +0.019 |
| Answer relevancy | 0.299 | **0.875** | **+0.576** |
| Context recall | 0.208 | **0.854** | **+0.646** |
| Context precision | 0.200 | **0.887** | **+0.687** |

4개 중 3개 메트릭이 0.58~0.69 만큼 점프합니다. Faithfulness가 거의 안 움직이는 이유는 둘 다 이미 정직하게 답변에 grounding을 시키기 때문 — 차이는 *환각하느냐*가 아니라 *애초에 맞는 context를 가져왔는가*입니다. 마지막 한 문장이 이 글 전체의 핵심.

헤드라인은 코퍼스를 50편 → 100편으로 키워도 유지됩니다. 라우팅도 안정적이고(agent가 40개 중 32개를 vector route로 보냄, 7개 local, 1개 global), rerank 단계 하나가 answer relevancy 개선분(+0.084 over no-rerank)의 대부분을 차지합니다 — 다만 context recall은 0.025만큼 *손해*를 봅니다(표준 retrieve+rerank trade-off).

## 가장 흥미로운 부분: baseline answer relevancy가 왜 0.30인가

리뷰어가 제일 먼저 물을 질문, 당연히. RAGAS의 answer_relevancy 메트릭은 "the provided summaries do not contain that information" 같은 *헷지 답변*을 **0**으로 매깁니다 — 그 답변이 얼마나 faithful하든 상관없이. baseline 답변을 분해해보면:

![Hedging](https://raw.githubusercontent.com/parkjongmin-ddam/graphrag-paper/main/docs/figures/fig4-hedging-decomposition.png)

- **Global** 모드: 40개 중 **28개**가 헷지. 평균 answer relevancy 0.033.
- **Local** 모드: 25개 헷지. 그러나 *직접 답한* 15개는 평균 **0.610**.
- baseline의 **faithfulness는 0.853 유지** — 헷지는 *정직한* 것이지, 환각이 아닙니다.

이게 *결과의 의미*를 바꿉니다. baseline의 낮은 점수는 메트릭 버그가 아닙니다: community summary와 1-hop subgraph는 질문이 묻는 *구체적인 숫자/파라미터*를 실제로 담고 있지 않으니, 모델이 정직하게 "모르겠다"고 답합니다. agent의 passage retrieval(과 reranker)이 메우는 게 정확히 그 공백입니다 — *진짜이고, 공정한* 개선.

*다만* answer relevancy 격차의 *크기*(+0.576)는 noncommittal-→-0 페널티에 의해 *증폭*돼 있습니다. 그래서 만약 회의적인 사람에게 숫자 하나만 내세운다면, **context recall(+0.646)과 context precision(+0.687)**이 최고의 증거 — retrieval 품질을 직접 재고, 답변 표현이나 헷지에 영향받지 않기 때문. answer relevancy는 corroborating evidence로, noncommittal caveat을 명시하면서 같이 보고합니다.

이 프로젝트에서 가장 쓸모 있었던 교훈: RAGAS 류의 noncommittal 감지를 쓰는 어떤 RAG 평가에서든, **answer_relevancy 옆에 noncommittal rate를 함께 보고하세요.** 이게 없으면 "내 시스템이 더 좋아진 것"인지 "내 baseline이 더 정중해졌을 뿐"인지 구분할 수 없습니다.

## 논문에 잘 안 적는 방법론적 교훈

50편 → 100편으로 키우는 중간에, 절반 가까운 논문이 그래프에 **0개 엔티티**를 기여하고 있다는 걸 발견했습니다. 왜? 엔티티 추출기의 `MAX_TOKENS=2000` 때문. 풀텍스트 논문(intro + related work)에서 엔티티/관계 JSON 출력이 2000 토큰을 넘어가면 중간에 잘리고, 잘린 JSON은 파싱 실패해 조용히 `[]`를 반환합니다. 파이프라인은 "ok"라고 보고했지만 그래프는 반쯤 비어 있었습니다.

cap을 8000으로 올리니 실패율이 ~50%에서 ~1%로 떨어졌고, 그래프가 503ent/532rel(50p, 망가진 상태)에서 1,342ent/1,489rel(100p, 수정된 상태)로 늘어났습니다. 그래서 50→100 비교에는 두 변화가 섞입니다(논문 수 증가 + truncation 버그 수정) — 이건 숨기지 않고 보고서에 명시.

일반화된 교훈: LLM을 구조적 추출기로 쓸 때는, **파싱 성공률을 검증하세요**. 단순히 "파이프라인이 끝까지 돌았다"가 아니라. 조용한 0은 시끄러운 에러보다 더 나쁩니다.

## 2차 judge로 cross-check

LLM-as-judge의 흔한 우려: judge가 평가 대상과 같은 모델군이면 self-preference가 끼지 않느냐. 확인하려고, 답변과 컨텍스트는 그대로 고정하고 같은 레코드를 **OpenAI gpt-4o-mini**(완전히 다른 모델군)로 다시 채점했습니다. 4지표 모두 부호 유지 — *agent ≫ baseline*은 **judge-robust**. answer relevancy가 두 judge에서 가장 일관(Δ +0.576 vs +0.544, 약 5% 차이). context 지표의 *크기*는 OpenAI 쪽에서 baseline에 더 관대해 줄어들지만(+0.45 recall, +0.32 precision), agent 우위는 여전히 큼. 흥미롭게도, OpenAI는 context 지표·faithfulness에서 agent를 *Claude보다 더 높게* 평가합니다 — Claude self-preference의 증거는 없음. 자세한 수치는 paper §6.2에 있고, 재현은 `python -m eval.judge_ablation`.

## 그리고 인간이 직접 쓴 질문에서도?

당연히 회의적인 사람이 다음으로 던질 질문: *"40개 질문이 LLM이 만든 거잖아. agent도 LLM이고. 당연히 잘 답하지."* 이게 합성-질문-편의(synthetic-convenience) 비판입니다. 답하려고 **사람이 처음부터 손으로 작성한 15개 별도 질문셋**을 만들었습니다 — 5 카테고리(fact 5 / compare 3 / multi-hop 3 / method 2 / ambiguous 2), 18개 paper에서, *합성 40개 질문이 한 번도 사용하지 않은 paper만 골라서*.

**중요한 디테일**: 측정 *전*에 임계값을 *사전 등록*했습니다 — Δ ≥ 0.40이면 "강함, 일반화 OK", 0.20–0.40이면 "축소됐으나 우위 유지, 합성 편의 효과 있음", < 0.20이면 "합성 편의가 결과의 큰 부분, 헤드라인 약화". *결과 본 뒤에* 유리한 기준을 만드는 짓을 막기 위함.

결과 (agent − baseline_best Δ, human n=15 vs synthetic n=40):

| Metric | synth (Claude) | human (Claude) | synth (OpenAI) | human (OpenAI) |
|---|---|---|---|---|
| answer relevancy | +0.576 | +0.480 | +0.544 | +0.350 |
| context recall | +0.646 | **+0.433** | +0.454 | **+0.567** |
| context precision | +0.687 | +0.400 | +0.323 | +0.333 |

세 가지 정직한 결론:

1. **헤드라인은 인간 작성 질문에서도 살아남는다.** 4지표 모두 부호 양수, 두 judge 모두에서.
2. **합성-편의 효과는 실재한다.** synth Δ가 human Δ보다 일관되게 ~0.10–0.30 큼. 우리가 의심한 효과가 실제 있었고, 그 *크기까지* 정직하게 측정 — 숨기지 않음.
3. **context recall이 모든 검증 단계를 통과한다.** ≥0.40 "강화" 임계값을 *두 judge 모두에서* 통과 (+0.433 / +0.567). 표현 독립적(§4) + judge 독립적(§5) + 합성 편향 독립적(여기) — **단일 가장 견고한 증거**.

자세한 수치·사전 등록 임계값은 paper §6.3, 재현은 `python -m eval.eval_human`.

## 직접 돌려보기

```bash
git clone https://github.com/parkjongmin-ddam/graphrag-paper && cd graphrag-paper
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # 또는 .env 파일에
python run_pipeline.py --list
python run_pipeline.py --only agent_eval --allow-network --force
```

아니면 [Markdown 리포트](https://github.com/parkjongmin-ddam/graphrag-paper/blob/main/docs/PAPER.md)나 [컴파일된 PDF](https://github.com/parkjongmin-ddam/graphrag-paper/blob/main/docs/paper.pdf)를 그냥 읽어보세요. 그림 7개는 eval JSON에서 결정론적으로 `python docs/figures/make_figures.py`로 재생성됩니다.

---

*코드·논문·평가 산출물: <https://github.com/parkjongmin-ddam/graphrag-paper>. MIT 라이선스. Issue·PR 환영합니다.*

*초안은 AI 도움으로 다듬었습니다. 실험·코드·분석은 모두 직접 한 것입니다.*

---