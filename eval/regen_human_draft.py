"""
GraphRAG-Paper - (Re)generate human-authored questions draft with Korean help
--------------------------------------------------
Builds docs/questions_human_draft.md from a fixed selection of 15 questions
across 5 categories (18 papers — multi-hop pairs share two papers per question).

For each question block we render:
  - the paper title (year)
  - a 1-sentence Korean summary of the paper (for fast skim)
  - the full English abstract + intro excerpt (THE source-of-truth for the GT)
  - the suggested framing in English AND Korean
  - empty Q / GT slots for the human to fill

Run from project root:
    python -m eval.regen_human_draft
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path("docs/questions_human_draft.md")

# Paper selections per category. Each entry: (paper_id, suggested_framing_en, summary_ko, framing_ko)
PICKS_FACT = [
    (
        "28e2ecb4183ebc0eec504b12dddc677f8aef8745",
        "How many tasks does the benchmark cover, and what RAG capabilities does it measure?",
        "RGB 벤치마크로 RAG의 4가지 핵심 능력(노이즈 강건성, 부정 거부, 정보 통합, 반사실 강건성)을 평가하고 6개 LLM을 비교한 논문.",
        "RGB 벤치마크가 평가하는 RAG의 능력은 몇 가지이고, 무엇무엇인가?",
    ),
    (
        "daebec92963ab8dea492f0c209bdf57e87bcaa07",
        "How many algorithms and datasets does FlashRAG support?",
        "16개 RAG 알고리즘과 38개 벤치마크 데이터셋을 통합한 모듈형 오픈소스 RAG 툴킷.",
        "FlashRAG가 지원하는 알고리즘 수와 데이터셋 수는?",
    ),
    (
        "8212d4df209a2586f5ae375ea21622ee1dc0cb12",
        "What chunk size does this study recommend for long-document retrieval, and across how many datasets?",
        "장문 문서 검색에서 청크 크기가 retrieval 품질에 미치는 영향을 여러 데이터셋에서 분석한 연구.",
        "이 연구가 권장하는 장문 검색용 청크 크기는, 그리고 몇 개 데이터셋에서 검증됐는가?",
    ),
    (
        "ba454ba8c594dfb86c25dff2e265c8a2686aa037",
        "List the seven failure points the paper identifies.",
        "실제 RAG 시스템 구축 시 마주치는 7가지 실패 지점을 사례 연구로 정리한 논문.",
        "논문이 식별한 7가지 RAG 실패 지점은 무엇무엇인가?",
    ),
    (
        "7e55d8701785818776323b4147cb13354c820469",
        "On which scientific QA benchmark and with what accuracy does PaperQA report results?",
        "과학 논문 풀텍스트에 대해 검색→컨텍스트 구성→답변·인용 생성을 단계별로 수행하는 RAG 에이전트.",
        "PaperQA는 어떤 과학 QA 벤치마크에서 어느 정도의 정확도를 보고하는가?",
    ),
]

PICKS_COMPARE = [
    (
        "5af10e53941c4256cdd8d27b04eb1ca8f1f76218",
        "Which two generation paradigms does the paper compare, and on what dimension?",
        "서로 다른 RAG 검색-생성 패러다임들을 동일 조건에서 비교 분석한 논문.",
        "논문이 비교하는 두 생성 방식은 무엇이고, 어떤 차원에서 비교했는가?",
    ),
    (
        "f92fd02f5bc38802d7ddd91b4bc4e3001573f5d6",
        "How does HopRAG handle multi-hop reasoning compared to standard single-step retrieval?",
        "HopRAG는 multi-hop 질문을 위해 논리 기반 reasoning graph를 사용하는 RAG.",
        "HopRAG가 단일 단계 검색과 비교해 multi-hop 추론을 어떻게 다르게 다루는가?",
    ),
    (
        "c3788ddba6a255a09eb969b5a8ccd2d5921f53bd",
        "How does HypRAG's hyperbolic embedding compare to Euclidean dense retrieval?",
        "HypRAG는 하이퍼볼릭 임베딩 공간에서 dense retrieval을 수행하는 방식 제안.",
        "HypRAG의 hyperbolic 임베딩이 일반적인 Euclidean dense retrieval과 어떻게 다른가?",
    ),
]

# Multi-hop: 3 questions, each pairs 2 papers. (pidA, summary_koA, pidB, summary_koB, framing_en, framing_ko)
PICKS_MULTIHOP = [
    (
        "6489640b1d30a8a3e7cb906bb6557f1ccd0d799d",
        "Chain-of-Note: 검색된 노트마다 단계별 사고 노트를 생성·검토해 RAG 견고성을 높이는 기법.",
        "e8a9b5a32836af499dcb9ccdee1008638309a6cc",
        "InstructRAG: 검색 결과의 신뢰도를 모델이 스스로 검증·합리화하는 self-synthesized rationale 학습 방식.",
        "How do Chain-of-Note and InstructRAG each try to improve RAG robustness through self-* mechanisms, and how do their approaches differ?",
        "Chain-of-Note와 InstructRAG가 self-* 방식으로 RAG 견고성을 높이는 두 방식의 공통점과 차이는?",
    ),
    (
        "b63bb769ac924c5411704331071333515b2f5190",
        "Adversarial Hubness Detector: RAG 검색기에 hubness poisoning이라는 적대적 공격을 가하고 탐지하는 기법.",
        "37845b206ddf48fc757285472159a5198fd320d7",
        "ProGRank: probe-gradient 기반 리랭킹으로 corpus poisoning을 방어하는 RAG 보안 기법.",
        "What kind of attack does the Adversarial Hubness Detector identify, and how does ProGRank's reranking defense respond to it?",
        "Adversarial Hubness Detector가 다루는 공격을 ProGRank의 리랭킹 방어는 어떻게 대응하는가?",
    ),
    (
        "2c74686c061a8381f515311aa41b75113019f313",
        "MG2-RAG: 다중 granularity 멀티모달 그래프를 활용한 multimodal RAG.",
        "226787d438bc47f986f82625d6b74fa6f733ef60",
        "M3DocRAG: 다중 페이지·다중 문서 환경의 멀티모달 RAG.",
        "How do MG2-RAG and M3DocRAG differ in the granularity / unit at which they retrieve multimodal evidence?",
        "MG2-RAG와 M3DocRAG는 멀티모달 근거를 검색하는 단위/granularity 측면에서 어떻게 다른가?",
    ),
]

PICKS_METHOD = [
    (
        "1cc6cc4960f7df59e7813d9a8e11098d0a0d0720",
        "When does DRAGIN decide to trigger retrieval?",
        "DRAGIN은 LLM의 실시간 정보 필요 신호(uncertainty/attention)에 기반해 동적으로 검색을 트리거하는 RAG.",
        "DRAGIN은 어떤 신호를 사용해 retrieval을 trigger하는가?",
    ),
    (
        "c4aeec57b9ad4fa36cbd9bdad05dbbbd340183df",
        "What does ARL2 align between retrievers and black-box LLMs?",
        "ARL2는 black-box LLM과 retriever를 self-guided adaptive relevance labeling으로 정렬하는 학습 방식.",
        "ARL2는 retriever와 black-box LLM 사이에서 무엇을 정렬하는가?",
    ),
]

PICKS_AMBIG = [
    (
        "45ed289c810d1d7025a2597c66b0e21c592c02a7",
        "How does the survey categorize the architectural variants of RAG?",
        "RAG의 아키텍처·강화기법·평가·응용을 전반적으로 다룬 서베이 논문.",
        "이 서베이는 RAG 아키텍처를 어떻게 분류·정리하는가?",
    ),
    (
        "d48032843bc08c95c0fa71d82818afb34bba55b0",
        "Why does the paper frame RAG as a cooperative decision-making problem?",
        "RAG의 검색기-LLM 상호작용을 협력적 의사결정 문제로 재정식화하는 개념적 프레임워크.",
        "논문은 왜 RAG를 협력적 의사결정 문제로 보는가?",
    ),
]


def _excerpt(d: dict) -> tuple[str, str]:
    abs_ = (d.get("abstract") or "").strip()
    intro = (d.get("intro") or "").strip()
    return abs_, intro[:1800] if intro else ""


def _single_block(qnum: int, pid: str, framing_en: str, summary_ko: str, framing_ko: str, papers: dict) -> list[str]:
    d = papers[pid]
    abs_, intro = _excerpt(d)
    aid = d.get("arxiv_id")
    out = []
    out.append(f"\n### Q{qnum} — paper: `{pid}`")
    out.append(f"**Title**: {d.get('title') or ''}  (year: {d.get('year')})")
    if aid:
        out.append(f"**arXiv**: <https://arxiv.org/abs/{aid}>  ·  **full corpus**: `data/corpus/{pid}.json`")
    out.append(f"\n**한글 요약**: {summary_ko}")
    out.append(f"\n**Abstract**:")
    out.append(f"> {abs_}")
    if intro:
        out.append(f"\n**Intro excerpt** (앞 1800자; 전체는 corpus JSON 참고):")
        out.append(f"> {intro}")
    out.append(f"\n**Suggested framing (EN)**: {framing_en}")
    out.append(f"**제안된 방향 (KO)**: {framing_ko}")
    out.append(f"\n**Q**: [FILL IN]")
    out.append(f"**GT**: [FILL IN]")
    return out


def _pair_block(qnum: int, pidA: str, sumA: str, pidB: str, sumB: str, framing_en: str, framing_ko: str, papers: dict) -> list[str]:
    dA, dB = papers[pidA], papers[pidB]
    out = []
    out.append(f"\n### Q{qnum} — papers: `{pidA}` + `{pidB}`")
    out.append(f"**Paper A**: {dA.get('title') or ''}  (year: {dA.get('year')})")
    if dA.get("arxiv_id"):
        out.append(f"**arXiv A**: <https://arxiv.org/abs/{dA.get('arxiv_id')}>  ·  `data/corpus/{pidA}.json`")
    out.append(f"**한글 요약 A**: {sumA}")
    out.append(f"> {(dA.get('abstract') or '').strip()}")
    out.append(f"\n**Paper B**: {dB.get('title') or ''}  (year: {dB.get('year')})")
    if dB.get("arxiv_id"):
        out.append(f"**arXiv B**: <https://arxiv.org/abs/{dB.get('arxiv_id')}>  ·  `data/corpus/{pidB}.json`")
    out.append(f"**한글 요약 B**: {sumB}")
    out.append(f"> {(dB.get('abstract') or '').strip()}")
    out.append(f"\n**Suggested framing (EN)**: {framing_en}")
    out.append(f"**제안된 방향 (KO)**: {framing_ko}")
    out.append(f"\n**Q**: [FILL IN]")
    out.append(f"**GT**: [FILL IN]")
    return out


def main() -> None:
    papers = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in Path("data/corpus").glob("*.json")}

    out: list[str] = []
    out.append("# Human-Authored Questions — Draft template (15 questions)")
    out.append("")
    out.append("## 작성 가이드 (한국어)")
    out.append("")
    out.append("각 질문 블록에는 **한글 요약** + **영문 abstract/intro** + **제안된 방향(EN/KO 둘 다)** 이 포함돼 있습니다. 한글 요약으로 빠르게 paper를 파악하고, 영문 passage를 보면서 **Q (영문 질문)** 와 **GT (영문 1~2문장 답변, passage 안에서 근거 있는 표현 사용)** 를 채우세요.")
    out.append("")
    out.append("- `**Q**: [FILL IN]` 의 `[FILL IN]` 만 골라 지우고 영문 질문을 타이핑")
    out.append("- `**GT**: [FILL IN]` 의 `[FILL IN]` 만 골라 지우고 영문 1~2문장 ground-truth를 타이핑")
    out.append("- `### Q1 — paper: ...` 헤더 줄과 `한글 요약`, `Abstract`, `Intro excerpt` 줄은 **건드리지 마세요** (paper_id 매핑·grounding 기준)")
    out.append("- Multi-hop(Q9·Q10·Q11)은 Paper A와 B 두 abstract를 모두 보고 **둘 다 필요한 질문**을 작성")
    out.append("- 한국어가 편하시면 한국어로 쓰셔도 됩니다만, RAG agent·judge가 모두 영문 모델이라 **영문 권장**")
    out.append("- 30개 `[FILL IN]` 채우고 **Ctrl+S로 저장**, 끝나면 알려주세요")
    out.append("")
    out.append("## How to fill (English)")
    out.append("")
    out.append("Each question block contains a Korean 1-sentence summary (한글 요약) for quick skimming, the full English passage(s), and a suggested framing in both EN and KO. Replace each `[FILL IN]` with your text. Keep all other lines intact — paper IDs and the passages are how the parser maps your answers back to the source.")
    out.append("")

    qnum = 0

    out.append("\n## 1. Fact-specific (5 questions)")
    out.append("")
    out.append("*구체적인 숫자, 카운트, 점수, 또는 passage에 등장하는 고유명사를 묻는 질문. / Ask for a concrete number, count, score, or named entity that appears in the passage.*")
    for pid, fr_en, sum_ko, fr_ko in PICKS_FACT:
        qnum += 1
        out.extend(_single_block(qnum, pid, fr_en, sum_ko, fr_ko, papers))

    out.append("\n## 2. Comparative (3 questions)")
    out.append("")
    out.append("*두 가지(방법·모델·검색기·패러다임)가 어떻게 다른지 묻는 질문. / Ask how two things — methods, retrievers, models, paradigms — differ, using the passage.*")
    for pid, fr_en, sum_ko, fr_ko in PICKS_COMPARE:
        qnum += 1
        out.extend(_single_block(qnum, pid, fr_en, sum_ko, fr_ko, papers))

    out.append("\n## 3. Multi-hop pairs (3 questions, from 6 papers in pairs)")
    out.append("")
    out.append("*Paper A와 Paper B 두 passage가 모두 필요한 질문 하나를 작성하세요. / Write one question that requires BOTH papers' passages to answer.*")
    for pidA, sumA, pidB, sumB, fr_en, fr_ko in PICKS_MULTIHOP:
        qnum += 1
        out.extend(_pair_block(qnum, pidA, sumA, pidB, sumB, fr_en, fr_ko, papers))

    out.append("\n## 4. Methodological (2 questions)")
    out.append("")
    out.append("*왜/어떻게 어떤 메커니즘이 작동하는지(인과/과정) 묻는 질문. / Ask why or how a mechanism works (causal/process question).*")
    for pid, fr_en, sum_ko, fr_ko in PICKS_METHOD:
        qnum += 1
        out.extend(_single_block(qnum, pid, fr_en, sum_ko, fr_ko, papers))

    out.append("\n## 5. Ambiguous (2 questions)")
    out.append("")
    out.append("*넓고 열린 질문. GT는 passage가 뒷받침하는 한도 안에서 '시스템이 이렇게 답하면 충분하다'는 모범 답안을 작성. / Broad/open-ended; GT is the passage-supported answer the system *should* give.*")
    for pid, fr_en, sum_ko, fr_ko in PICKS_AMBIG:
        qnum += 1
        out.extend(_single_block(qnum, pid, fr_en, sum_ko, fr_ko, papers))

    text = "\n".join(out) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"questions: {qnum}")
    print(f"size: {len(text)} chars")


if __name__ == "__main__":
    main()
