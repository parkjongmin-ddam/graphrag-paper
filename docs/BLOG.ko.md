# GraphRAG에서 Agentic RAG로, 정직하게 측정해보기

*RAG 논문 100편 코퍼스에서 agentic loop가 GraphRAG baseline을 정말로 이기는지, 그리고 그 숫자를 *자기 자신*을 속이지 않고 읽는 법.*

📄 [논문 PDF](https://github.com/parkjongmin-ddam/graphrag-paper/blob/main/docs/paper.pdf) · 💻 [GitHub 코드](https://github.com/parkjongmin-ddam/graphrag-paper) · 📝 [Markdown 리포트](https://github.com/parkjongmin-ddam/graphrag-paper/blob/main/docs/PAPER.md)

요즘 Agentic RAG 논문들은 큰 숫자를 보여줍니다. 저는 그게 *baseline을 고정하고, 같은 질문을 양쪽에 던지고, 숫자가 왜 움직였는지를 진지하게 들여다봤을 때도* 얼마나 살아남는지 알고 싶었습니다. 그래서 RAG 논문 100편을 코퍼스로 **GraphRAG**를 처음부터 직접 구현하고, 그 위에 **agentic loop**를 얹은 뒤, 같은 40개 질문을 양쪽에 던졌습니다. 이 글은 그 결과의 읽기 쉬운 버전입니다.

## 무엇을 만들었나

**Phase A — GraphRAG (baseline).** Semantic Scholar의 forward citation으로 RAG 논문 100편을 모읍니다. Claude가 도메인 스키마(Method, Model, Dataset, Metric, Task, Author, Institution, Paper + 7가지 relation)에 맞춰 엔티티/관계 그래프를 추출하고, Leiden community detection을 돌린 뒤 큰 community마다 LLM으로 요약을 생성합니다. 두 가지 검색 모드: *global*(community summary들을 concatenate해서 답변), *local*(쿼리에서 substring으로 seed 엔티티를 찾고 1-hop subgraph로 확장 → 논문 발췌문과 함께 답변). 질문당 LLM 호출 한 번. 결정적이고, **고정**(frozen)되어 있어 baseline이 움직이지 않습니다.

**Phase B — Agentic RAG (loop).** Phase A의 (고정된) 검색기 위에 LangGraph DAG를 얹습니다:

```
START → route → search → grade ─┬─ sufficient ───────────→ reflect ─┬─ END
                                └─ insufficient → rewrite →         │
                                                  escalate ─────────┘
                                                                    │
                                                  hallucinated → regenerate → END
```

세 번째 검색기 — chunk 단위 dense passage retrieval — 가 추가됩니다. 모든 vector 질의는 **cross-encoder reranker**(B-M6)를 거쳐 retrieve-24 → rerank → top-8 패턴으로 동작합니다. 각 조건부 분기는 *bounded single retry*: 루프 없음, 죽음의 무한 반복 없음. LLM 호출마다 fail-safe 기본값(grader는 파싱 실패 시 "sufficient", reflector는 "grounded")이 있어, 한 번 흔들리는 judge가 파이프라인 전체를 깨트리지 못합니다.

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

헤드라인은 코퍼스를 50편 → 100편으로 키워도 유지됩니다. 라우팅도 안정적이고(agent가 40개 중 32개를 vector route로 보냄, 7개 local, 1개 global), rerank 단계 하나만 따로 떼서 측정해도 answer relevancy의 대부분 개선분(+0.084 over no-rerank)을 그게 가져옵니다 — context recall이 0.025만큼 *손해* 보는 표준 retrieve+rerank trade-off와 함께.

## 가장 흥미로운 부분: baseline answer relevancy가 왜 0.30인가

리뷰어가 제일 먼저 물을 질문, 당연히. RAGAS의 answer_relevancy 메트릭은 "the provided summaries do not contain that information" 같은 *헷지 답변*을 **0**으로 매깁니다 — 그 답변이 얼마나 faithful하든 상관없이. baseline 답변을 분해해보면:

![Hedging](https://raw.githubusercontent.com/parkjongmin-ddam/graphrag-paper/main/docs/figures/fig4-hedging-decomposition.png)

- **Global** 모드: 40개 중 **28개**가 헷지. 평균 answer relevancy 0.033.
- **Local** 모드: 25개 헷지. 그러나 *직접 답한* 15개는 평균 **0.610**.
- baseline의 **faithfulness는 0.853 유지** — 헷지는 *정직한* 것이지, 환각이 아닙니다.

이게 *결과의 의미*를 바꿉니다. baseline의 낮은 점수는 메트릭 버그가 아닙니다: community summary와 1-hop subgraph는 질문이 묻는 *구체적인 숫자/파라미터*를 실제로 담고 있지 않으니, 모델이 정직하게 "모르겠다"고 답합니다. agent의 passage retrieval(과 reranker)이 메우는 게 정확히 그 공백입니다 — *진짜이고, 공정한* 개선.

*다만* answer relevancy 격차의 *크기*(+0.576)는 noncommittal-→-0 페널티에 의해 *증폭*돼 있습니다. 그래서 만약 회의적인 사람에게 숫자 하나만 변호한다면, **context recall(+0.646)과 context precision(+0.687)**이 최고의 증거 — retrieval 품질을 직접 재고, 답변 표현이나 헷지에 영향받지 않기 때문. answer relevancy는 corroborating evidence로, noncommittal caveat을 명시하면서 같이 보고합니다.

이 프로젝트에서 가장 쓸모 있었던 교훈: RAGAS 류의 noncommittal 감지를 쓰는 어떤 RAG 평가에서든, **answer_relevancy 옆에 noncommittal rate를 함께 보고하세요.** 이게 없으면 "내 시스템이 더 좋아진 것"인지 "내 baseline이 더 정중해졌을 뿐"인지 구분할 수 없습니다.

## 논문에 잘 안 적는 방법론적 교훈

50편 → 100편으로 키우는 중간에, 절반 가까운 논문이 그래프에 **0개 엔티티**를 기여하고 있다는 걸 발견했습니다. 왜? 엔티티 추출기의 `MAX_TOKENS=2000` 때문. 풀텍스트 논문(intro + related work)에서 엔티티/관계 JSON 출력이 2000 토큰을 넘어가면 중간에 잘리고, 잘린 JSON은 파싱 실패해 조용히 `[]`를 반환합니다. 파이프라인은 "ok"라고 보고했지만 그래프는 반쯤 비어 있었습니다.

cap을 8000으로 올리니 실패율이 ~50%에서 ~1%로 떨어졌고, 그래프가 503ent/532rel(50p, 망가진 상태)에서 1,342ent/1,489rel(100p, 수정된 상태)로 늘어났습니다. 그래서 50→100 비교에는 두 변화가 섞입니다(논문 수 증가 *and* truncation 버그 수정) — 이건 숨기지 않고 보고서에 명시.

일반화된 교훈: LLM을 구조적 추출기로 쓸 때는, **파싱 성공률을 검증하세요**. 단순히 "파이프라인이 끝까지 돌았다"가 아니라. 조용한 0은 시끄러운 에러보다 더 나쁩니다.

## 2차 judge로 cross-check

LLM-as-judge의 흔한 우려: judge가 평가 대상과 같은 모델군이면 self-preference가 끼지 않느냐. 확인하려고, 답변과 컨텍스트는 그대로 고정하고 같은 레코드를 **OpenAI gpt-4o-mini**(완전히 다른 모델군)로 다시 채점했습니다. 4지표 모두 부호 유지 — *agent ≫ baseline*은 **judge-robust**. answer relevancy가 두 judge에서 가장 일관(Δ +0.576 vs +0.544, 약 5% 차이). context 지표의 *크기*는 OpenAI 쪽에서 baseline에 더 관대해 줄어들지만(+0.45 recall, +0.32 precision), agent 우위는 여전히 큼. 흥미롭게도, OpenAI는 context 지표·faithfulness에서 agent를 *Claude보다 더 높게* 평가합니다 — Claude self-preference의 증거는 없음. 자세한 수치는 paper §6.2에 있고, 재현은 `python -m eval.judge_ablation`.

## 직접 돌려보기

```bash
git clone https://github.com/parkjongmin-ddam/graphrag-paper && cd graphrag-paper
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # 또는 .env 파일에
python run_pipeline.py --list
python run_pipeline.py --only agent_eval --allow-network --force
```

아니면 [Markdown 리포트](https://github.com/parkjongmin-ddam/graphrag-paper/blob/main/docs/PAPER.md)나 [컴파일된 PDF](https://github.com/parkjongmin-ddam/graphrag-paper/blob/main/docs/paper.pdf)를 그냥 읽어보세요. 그림 7개는 eval JSON에서 결정적으로 `python docs/figures/make_figures.py`로 재생성됩니다.

---

*코드·논문·평가 산출물: <https://github.com/parkjongmin-ddam/graphrag-paper>. MIT 라이선스. Issue·PR 환영합니다.*

*초안은 AI 도움으로 다듬었습니다. 실험·코드·분석은 모두 직접 한 것입니다.*

---

## 게시 메모 (작성자용, 게시 전 삭제)

이미지 링크는 GitHub raw 절대 URL이므로, **velog, brunch, LinkedIn, dev.to 등 외부 이미지를 받는 어떤 플랫폼에서도 그대로 붙여넣어 게시 가능**합니다. 추가 편집 불필요.

**velog** — Markdown 그대로 붙여넣기. 태그 추천: `rag`, `langgraph`, `agentic-rag`, `ragas`, `llm`.

**brunch** — Markdown 직접 지원 안 함. 본문 텍스트만 복사 → brunch 에디터에 붙여넣고 이미지는 개별 업로드(파일을 GitHub에서 다운로드 후). 표는 brunch에서 잘 안 보이니 bullet로 변환 권장.

**LinkedIn Articles** — Markdown 미지원. 본문 복사 → LinkedIn 에디터가 헤딩·리스트는 자동 처리. **표 2개는 bullet 요약으로 바꾸거나 스크린샷 첨부**. 첫 H1은 LinkedIn이 자동으로 제목 입력란으로 옮깁니다 — 거기 입력하면 됩니다.

**dev.to (영문 활동도 한다면)** — 영문 BLOG.md 쪽이 더 적합. dev.to용 frontmatter는 영문 BLOG.md 푸터 참조.

**개인 블로그 (Jekyll/Hugo/MDX)** — 그대로 복사하거나 이미지 경로를 본인 호스팅으로 교체.

게시 후 `README.md` 상단에 `**📰 블로그**: <url>` 한 줄 추가 → 이 게시 메모 섹션은 발행본에서 제거.
