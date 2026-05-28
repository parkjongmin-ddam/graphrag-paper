# Human-Authored Questions — Draft template (15 questions)

## 작성 가이드 (한국어)

각 질문 블록에는 **한글 요약** + **영문 abstract/intro** + **제안된 방향(EN/KO 둘 다)** 이 포함돼 있습니다. 한글 요약으로 빠르게 paper를 파악하고, 영문 passage를 보면서 **Q (영문 질문)** 와 **GT (영문 1~2문장 답변, passage 안에서 근거 있는 표현 사용)** 를 채우세요.

- `**Q**: [FILL IN]` 의 `[FILL IN]` 만 골라 지우고 영문 질문을 타이핑
- `**GT**: [FILL IN]` 의 `[FILL IN]` 만 골라 지우고 영문 1~2문장 ground-truth를 타이핑
- `### Q1 — paper: ...` 헤더 줄과 `한글 요약`, `Abstract`, `Intro excerpt` 줄은 **건드리지 마세요** (paper_id 매핑·grounding 기준)
- Multi-hop(Q9·Q10·Q11)은 Paper A와 B 두 abstract를 모두 보고 **둘 다 필요한 질문**을 작성
- 한국어가 편하시면 한국어로 쓰셔도 됩니다만, RAG agent·judge가 모두 영문 모델이라 **영문 권장**
- 30개 `[FILL IN]` 채우고 **Ctrl+S로 저장**, 끝나면 알려주세요

## How to fill (English)

Each question block contains a Korean 1-sentence summary (한글 요약) for quick skimming, the full English passage(s), and a suggested framing in both EN and KO. Replace each `[FILL IN]` with your text. Keep all other lines intact — paper IDs and the passages are how the parser maps your answers back to the source.


## 1. Fact-specific (5 questions)

*구체적인 숫자, 카운트, 점수, 또는 passage에 등장하는 고유명사를 묻는 질문. / Ask for a concrete number, count, score, or named entity that appears in the passage.*

### Q1 — paper: `28e2ecb4183ebc0eec504b12dddc677f8aef8745`
**Title**: Benchmarking Large Language Models in Retrieval-Augmented Generation  (year: 2023)
**arXiv**: <https://arxiv.org/abs/2309.01431>  ·  **full corpus**: `data/corpus/28e2ecb4183ebc0eec504b12dddc677f8aef8745.json`

**한글 요약**: RGB 벤치마크로 RAG의 4가지 핵심 능력(노이즈 강건성, 부정 거부, 정보 통합, 반사실 강건성)을 평가하고 6개 LLM을 비교한 논문.

**Abstract**:
> Retrieval-Augmented Generation (RAG) is a promising approach for mitigating the hallucination of large language models (LLMs). However, existing research lacks rigorous evaluation of the impact of retrieval-augmented generation on different large language models, which make it challenging to identify the potential bottlenecks in the capabilities of RAG for different LLMs. In this paper, we systematically investigate the impact of Retrieval-Augmented Generation on large language models. We analyze the performance of different large language models in 4 fundamental abilities required for RAG, including noise robustness, negative rejection, information integration, and counterfactual robustness. To this end, we establish Retrieval-Augmented Generation Benchmark (RGB), a new corpus for RAG evaluation in both English and Chinese. RGB divides the instances within the benchmark into 4 separate testbeds based on the aforementioned fundamental abilities required to resolve the case. Then we evaluate 6 representative LLMs on RGB to diagnose the challenges of current LLMs when applying RAG. Evaluation reveals that while LLMs exhibit a certain degree of noise robustness, they still struggle significantly in terms of negative rejection, information integration, and dealing with false information. The aforementioned assessment outcomes indicate that there is still a considerable journey ahead to effectively apply RAG to LLMs.

**Intro excerpt** (앞 1800자; 전체는 corpus JSON 참고):
> Recently, there have been impressive advancements in large language models (LLMs) like ChatGPT [cite] and ChatGLM [cite]. Although these models have shown remarkable general abilities [cite], they still suffer severely from challenges including factual hallucination [cite], knowledge out-dating [cite], and the lack of domain-specific expertise [cite].

Incorporating external knowledge via information retrieval, i.e., Retrieval-Augmented 
Generation (RAG), has been regarded as a promising way to resolve the above challenges.  [cite]. With the help of external knowledge, LLMs can generate more accurate and reliable responses. The most common method is to use a search engine as a retriever such as New Bing. Due to the vast amount of information available on the Internet, using a search engine can provide more real-time information.

 < g r a p h i c s >

Illustration of 4 kinds of abilities required for retrieval-augmented generation of LLMs.

However, Retrieval-Augmented Generation brings not only positive effects to LLMs [cite]. On one hand, there is a significant amount of noise information even fake news in the content available on the Internet, which poses challenges for search engines in accurately retrieving desirable knowledge. On the other hand, LLMs suffer from unreliable generation challenge. LLMs can be misled by incorrect information contained in the context [cite] and also suffer from hallucination during the generation [cite], resulting in generating content that goes beyond external information. These challenges result in LLMs being unable to consistently generate reliable and accurate responses. Unfortunately, currently there lacks of comprehensive understanding on how these factors can influence RAG, and how could each model survives from these drawbacks 

**Suggested framing (EN)**: How many tasks does the benchmark cover, and what RAG capabilities does it measure?
**제안된 방향 (KO)**: RGB 벤치마크가 평가하는 RAG의 능력은 몇 가지이고, 무엇무엇인가?

**Q**: How many tasks does the benchmark cover, and what RAG capabilities does it measure?
**GT**:  We analyze the performance of different large language models in 4 fundamental abilities required for RAG, including noise robustness, negative rejection, information integration, and counterfactual robustness

### Q2 — paper: `daebec92963ab8dea492f0c209bdf57e87bcaa07`
**Title**: FlashRAG: A Modular Toolkit for Efficient Retrieval-Augmented Generation Research  (year: 2024)
**arXiv**: <https://arxiv.org/abs/2405.13576>  ·  **full corpus**: `data/corpus/daebec92963ab8dea492f0c209bdf57e87bcaa07.json`

**한글 요약**: 16개 RAG 알고리즘과 38개 벤치마크 데이터셋을 통합한 모듈형 오픈소스 RAG 툴킷.

**Abstract**:
> With the advent of large language models (LLMs) and multimodal large language models (MLLMs), the potential of retrieval-augmented generation (RAG) has attracted considerable research attention. However, the absence of a standardized framework for implementation, coupled with the inherently complex RAG process, makes it challenging and time-consuming for researchers to compare and evaluate these approaches in a consistent environment. In response to this challenge, we develop FlashRAG, an efficient and modular open-source toolkit designed to assist researchers in reproducing and comparing existing RAG methods and developing their own algorithms within a unified framework. Our toolkit has implemented 16 advanced RAG methods and gathered and organized 38 benchmark datasets. It has various features, including a customizable modular framework, a rich collection of pre-implemented RAG works, comprehensive datasets, efficient auxiliary pre-processing scripts, and extensive and standard evaluation metrics. Our toolkit and resources are available at https://github.com/RUC-NLPIR/FlashRAG.

**Intro excerpt** (앞 1800자; 전체는 corpus JSON 참고):
> In the era of large language models (LLMs), retrieval-augmented generation (RAG) [cite] has emerged as an effective solution to mitigate hallucination issues by leveraging external knowledge bases [cite]. The substantial applications and potential of RAG have attracted considerable research attention [cite]. However, with the introduction of a large number of new algorithms and models in recent years, comparing and evaluating these methods in a consistent setting has become increasingly challenging.

Many existing methods are not open-source or require specific configurations for implementation, making adaptation to custom data and innovative components challenging. The datasets and retrieval corpora often vary, with resources being scattered and requiring considerable pre-processing efforts. Besides, the inherent complexity of RAG systems, which involve indexing, retrieval, and generation, often demands extensive technical implementation. While there are some existing RAG toolkits such as LangChain [cite] and LlamaIndex [cite], they are typically complex and cumbersome, restricting researchers from tailoring processes to their specific needs. Therefore, there is a clear demand for a unified, research-focused RAG toolkit to simplify method development and facilitate comparative studies.

To address the aforementioned issues, we introduce , an open-source library that empowers researchers to reproduce, benchmark, and innovate within the RAG domain efficiently. This library offers built-in pipelines for replicating existing work, customizable components for crafting tailored RAG workflows, and streamlined access to organized datasets and corpora to accelerate research processes. provides a more researcher-friendly solution compared to existing toolkits. To summarize, the 

**Suggested framing (EN)**: How many algorithms and datasets does FlashRAG support?
**제안된 방향 (KO)**: 16 advanced RAG methods and 38 benchmark datasets

**Q**: How many algorithms and datasets does FlashRAG support?
**GT**: 16 advanced RAG methods and 38 benchmark datasets.

### Q3 — paper: `8212d4df209a2586f5ae375ea21622ee1dc0cb12`
**Title**: Rethinking Chunk Size For Long-Document Retrieval: A Multi-Dataset Analysis  (year: 2025)
**arXiv**: <https://arxiv.org/abs/2505.21700>  ·  **full corpus**: `data/corpus/8212d4df209a2586f5ae375ea21622ee1dc0cb12.json`

**한글 요약**: 장문 문서 검색에서 청크 크기가 retrieval 품질에 미치는 영향을 여러 데이터셋에서 분석한 연구.

**Abstract**:
> Chunking is a crucial preprocessing step in retrieval-augmented generation (RAG) systems, significantly impacting retrieval effectiveness across diverse datasets. In this study, we systematically evaluate fixed-size chunking strategies and their influence on retrieval performance using multiple embedding models. Our experiments, conducted on both short-form and long-form datasets, reveal that chunk size plays a critical role in retrieval effectiveness -- smaller chunks (64-128 tokens) are optimal for datasets with concise, fact-based answers, whereas larger chunks (512-1024 tokens) improve retrieval in datasets requiring broader contextual understanding. We also analyze the impact of chunking on different embedding models, finding that they exhibit distinct chunking sensitivities. While models like Stella benefit from larger chunks, leveraging global context for long-range retrieval, Snowflake performs better with smaller chunks, excelling at fine-grained, entity-based matching. Our results underscore the trade-offs between chunk size, embedding models, and dataset characteristics, emphasizing the need for improved chunk quality measures, and more comprehensive datasets to advance chunk-based retrieval in long-document Information Retrieval (IR).

**Intro excerpt** (앞 1800자; 전체는 corpus JSON 참고):
> Retrieval-Augmented Generation (RAG) has emerged as a powerful paradigm in natural language processing (NLP), enabling large language models (LLMs) to enhance response accuracy by incorporating relevant external knowledge retrieved from document corpora [cite] [cite]. This approach has significantly improved performance in knowledge-intensive tasks by mitigating the limitations of parametric memory in LLMs and enhancing factual consistency [cite]. The effectiveness of RAG systems heavily depend on document chunking strategies, which segment textual data into manageable units before retrieval. Among various chunking techniques, fixed-size token-based chunking remains a prevalent method due to its simplicity and ease of implementation [cite]. Fixed-size chunking segments documents into uniform token-length chunks, ensuring compatibility with transformer-based architectures that have strict token limits [cite].

 However, despite its widespread adoption, the robustness of this approach across varied document lengths remains underexplored. The effectiveness of fixed-size chunking can be influenced by factors such as information dispersion across chunks, redundancy in retrieval, and retrieval precision [cite]. Understanding these factors is crucial to optimizing retrieval performance and downstream generation quality in RAG applications.

 The importance of dataset characteristics in retrieval performance has been well established. Some datasets exhibit high answer locality, where relevant spans are concentrated within a few sentences, while others require reasoning over long contexts spanning multiple chunks [cite]. Recent studies have highlighted that datasets with diverse document structures demand adaptive chunking strategies to optimize retrieval effectiveness [cite]. A

**Suggested framing (EN)**: What chunk size does this study recommend for long-document retrieval, and across how many datasets?
**제안된 방향 (KO)**: 이 연구가 권장하는 장문 검색용 청크 크기는, 그리고 몇 개 데이터셋에서 검증됐는가?

**Q**: What chunk size does this study recommend for long-document retrieval, and across how many datasets?
**GT**: reveal that chunk size plays a critical role in retrieval effectiveness -- smaller chunks (64-128 tokens) are optimal for datasets with concise, fact-based answers, whereas larger chunks (512-1024 tokens) improve retrieval in datasets requiring broader contextual understanding.

### Q4 — paper: `ba454ba8c594dfb86c25dff2e265c8a2686aa037`
**Title**: Seven Failure Points When Engineering a Retrieval Augmented Generation System  (year: 2024)
**arXiv**: <https://arxiv.org/abs/2401.05856>  ·  **full corpus**: `data/corpus/ba454ba8c594dfb86c25dff2e265c8a2686aa037.json`

**한글 요약**: 실제 RAG 시스템 구축 시 마주치는 7가지 실패 지점을 사례 연구로 정리한 논문.

**Abstract**:
> Software engineers are increasingly adding semantic search capabilities to applications using a strategy known as Retrieval Augmented Generation (RAG). A RAG system involves finding documents that semantically match a query and then passing the documents to a large language model (LLM) such as ChatGPT to extract the right answer using an LLM. RAG systems aim to: a) reduce the problem of hallucinated responses from LLMs, b) link sources/references to generated responses, and c) remove the need for annotating documents with meta-data. However, RAG systems suffer from limitations inherent to information retrieval systems and from reliance on LLMs. In this paper, we present an experience report on the failure points of RAG systems from three case studies from separate domains: research, education, and biomedical. We share the lessons learned and present 7 failure points to consider when designing a RAG system. The two key takeaways arising from our work are: 1) validation of a RAG system is only feasible during operation, and 2) the robustness of a RAG system evolves rather than designed in at the start. We conclude with a list of potential research directions on RAG systems for the software engineering community.CCS CONCEPTS• Software and its engineering → Empirical software validation.

**Intro excerpt** (앞 1800자; 전체는 corpus JSON 참고):
> The new advancements of Large Language Models (LLMs), including ChatGPT, have given software engineers new capabilities to build new HCI solutions, complete complex tasks, summarise documents, answer questions in a given artefact(s), and generate new content. However, LLMs suffer from limitations when it comes to up-to-date knowledge or domain-specific knowledge currently captured in company's repositories. Two options to address this problem are: a) Finetuning LLMs (continue training an LLM using domain specific artifacts) which requires managing or serving a fine-tuned LLM; or b) use Retrieval-Augmented Generation (RAG) Systems that rely on LLMs for generation of answers using existing (extensible) knowledge artifacts. Both options have pros and cons related to privacy/security of data, scalability, cost, skills required, etc. In this paper, we focus on the RAG option.

Retrieval-Augmented Generation (RAG) systems offer a compelling solution to this challenge. By integrating retrieval mechanisms with the generative capabilities of LLMs, RAG systems can synthesise contextually relevant, accurate, and up-to-date information. A Retrieval-Augmented Generation (RAG) system combines information retrieval capabilities, and generative prowess of LLMs. The retrieval component focuses on retrieving relevant information for a user query from a data store. The generation component focuses on using the retrieved information as a context to generate an answer for the user query. RAG systems are an important use case as all unstructured information can now be indexed and available to query reducing development time no knowledge graph creation and limited data curation and cleaning.

Software engineers building RAG systems are expected to preprocess domain knowledge captured as artif

**Suggested framing (EN)**: List the seven failure points the paper identifies.
**제안된 방향 (KO)**: 논문이 식별한 7가지 RAG 실패 지점은 무엇무엇인가?

**Q**: [FILL IN]
**GT**: [FILL IN]

### Q5 — paper: `7e55d8701785818776323b4147cb13354c820469`
**Title**: PaperQA: Retrieval-Augmented Generative Agent for Scientific Research  (year: 2023)
**arXiv**: <https://arxiv.org/abs/2312.07559>  ·  **full corpus**: `data/corpus/7e55d8701785818776323b4147cb13354c820469.json`

**한글 요약**: 과학 논문 풀텍스트에 대해 검색→컨텍스트 구성→답변·인용 생성을 단계별로 수행하는 RAG 에이전트.

**Abstract**:
> Large Language Models (LLMs) generalize well across language tasks, but suffer from hallucinations and uninterpretability, making it difficult to assess their accuracy without ground-truth. Retrieval-Augmented Generation (RAG) models have been proposed to reduce hallucinations and provide provenance for how an answer was generated. Applying such models to the scientific literature may enable large-scale, systematic processing of scientific knowledge. We present PaperQA, a RAG agent for answering questions over the scientific literature. PaperQA is an agent that performs information retrieval across full-text scientific articles, assesses the relevance of sources and passages, and uses RAG to provide answers. Viewing this agent as a question answering model, we find it exceeds performance of existing LLMs and LLM agents on current science QA benchmarks. To push the field closer to how humans perform research on scientific literature, we also introduce LitQA, a more complex benchmark that requires retrieval and synthesis of information from full-text scientific papers across the literature. Finally, we demonstrate PaperQA's matches expert human researchers on LitQA.

**Intro excerpt** (앞 1800자; 전체는 corpus JSON 참고):
> The rate of papers published yearly grows at an exponential rate, with over 5 million academic articles published in 2022 [cite], and over 200 million articles in total [cite]. 
The difficulty of navigating this extensive literature means significant scientific findings have gone unnoticed for extended periods [cite]. Work in the last 10 years has sought to make the space of literature more manageable for scientists, with the introduction of keyword search systems [cite], vector similarity embeddings [cite] and recommender systems [cite]. 
The process of scientific discovery from literature is still, however, highly manual.

The use of Large Language Models (LLMs) to answer scientific questions is increasingly seen in academia and research-heavy professions such as medicine [cite].
While LLMs can produce answers faster and encompass a broader, deeper scope than manual searching, there is a high risk of hallucination in responses, which can lead to potentially dangerous outcomes [cite]. 
Incorrect information can be more damaging than no information at all, as the time to verify veracity can take just as long as retrieving it from research papers in the first place [cite].
Reliance on pre-trained LLMs also prevents the discovery of new information published after a training cutoff date. 
Given the rapidly moving pace of science, this can lead to misconceptions persisting. 

Retrieval-Augmented Generation (RAG) models are a potential solution to these limitations [cite].
RAG models retrieve text from a corpus, using methods such as vector embedding search or keyword search, and add the retrieved passage to the context window of the LLM. 
RAG usage can reduce hallucinations in conversations and improve LLM performance on QA tasks [cite]. Nevertheless, standard RAG models f

**Suggested framing (EN)**: On which scientific QA benchmark and with what accuracy does PaperQA report results?
**제안된 방향 (KO)**: PaperQA는 어떤 과학 QA 벤치마크에서 어느 정도의 정확도를 보고하는가?

**Q**: [FILL IN]
**GT**: [FILL IN]

## 2. Comparative (3 questions)

*두 가지(방법·모델·검색기·패러다임)가 어떻게 다른지 묻는 질문. / Ask how two things — methods, retrievers, models, paradigms — differ, using the passage.*

### Q6 — paper: `5af10e53941c4256cdd8d27b04eb1ca8f1f76218`
**Title**: From Retrieval to Generation: Comparing Different Approaches  (year: 2025)
**arXiv**: <https://arxiv.org/abs/2502.20245>  ·  **full corpus**: `data/corpus/5af10e53941c4256cdd8d27b04eb1ca8f1f76218.json`

**한글 요약**: 서로 다른 RAG 검색-생성 패러다임들을 동일 조건에서 비교 분석한 논문.

**Abstract**:
> Knowledge-intensive tasks, particularly open-domain question answering (ODQA), document reranking, and retrieval-augmented language modeling, require a balance between retrieval accuracy and generative flexibility. Traditional retrieval models such as BM25 and Dense Passage Retrieval (DPR), efficiently retrieve from large corpora but often lack semantic depth. Generative models like GPT-4-o provide richer contextual understanding but face challenges in maintaining factual consistency. In this work, we conduct a systematic evaluation of retrieval-based, generation-based, and hybrid models, with a primary focus on their performance in ODQA and related retrieval-augmented tasks. Our results show that dense retrievers, particularly DPR, achieve strong performance in ODQA with a top-1 accuracy of 50.17\% on NQ, while hybrid models improve nDCG@10 scores on BEIR from 43.42 (BM25) to 52.59, demonstrating their strength in document reranking. Additionally, we analyze language modeling tasks using WikiText-103, showing that retrieval-based approaches like BM25 achieve lower perplexity compared to generative and hybrid methods, highlighting their utility in retrieval-augmented generation. By providing detailed comparisons and practical insights into the conditions where each approach excels, we aim to facilitate future optimizations in retrieval, reranking, and generative models for ODQA and related knowledge-intensive applications.

**Intro excerpt** (앞 1800자; 전체는 corpus JSON 참고):
> The increasing complexity of knowledge-intensive tasks, particularly open-domain question answering (ODQA) and retrieval-augmented applications, necessitates advanced approaches to efficiently retrieve and generate relevant information. Traditionally, retrieval-based methods have played a central role in these tasks, with models like BM25 [cite] serving as foundational tools for extracting relevant documents. However, the limitations of keyword-based retrieval prompted the development of dense retrieval models such as Dense Passage Retrieval (DPR) [cite] and Contriever [cite], which leverage transformer-based architectures to encode queries and documents into dense representations. While dense retrieval models improve over sparse methods, they introduce new challenges. First, retrieval corpora are typically divided into fixed chunks [cite], which can lead to retrieving irrelevant content. Second, dual-encoder architectures encode queries and documents separately, limiting direct interaction between them [cite]. Finally, dense retrieval models require pre-encoding and storing document embeddings, which constrains scalability and hinders their ability to leverage large language models (LLMs) [cite].

To address these limitations, generative models such as GPT-3.5 and InstructGPT [cite] offer an alternative by directly generating contextualized responses instead of retrieving existing documents. Approaches like GenRead [cite] first generate relevant text and then use it for answer prediction. However, generative models often struggle with factual consistency and may hallucinate information [cite], making them less reliable for knowledge-intensive tasks.

Given the trade-offs between retrieval and generation, hybrid models have emerged to integrate the strengths of both app

**Suggested framing (EN)**: Which two generation paradigms does the paper compare, and on what dimension?
**제안된 방향 (KO)**: 논문이 비교하는 두 생성 방식은 무엇이고, 어떤 차원에서 비교했는가?

**Q**: [FILL IN]
**GT**: [FILL IN]

### Q7 — paper: `f92fd02f5bc38802d7ddd91b4bc4e3001573f5d6`
**Title**: HopRAG: Multi-Hop Reasoning for Logic-Aware Retrieval-Augmented Generation  (year: 2025)
**arXiv**: <https://arxiv.org/abs/2502.12442>  ·  **full corpus**: `data/corpus/f92fd02f5bc38802d7ddd91b4bc4e3001573f5d6.json`

**한글 요약**: HopRAG는 multi-hop 질문을 위해 논리 기반 reasoning graph를 사용하는 RAG.

**Abstract**:
> Retrieval-Augmented Generation (RAG) systems often struggle with imperfect retrieval, as traditional retrievers focus on lexical or semantic similarity rather than logical relevance. To address this, we propose \textbf{HopRAG}, a novel RAG framework that augments retrieval with logical reasoning through graph-structured knowledge exploration. During indexing, HopRAG constructs a passage graph, with text chunks as vertices and logical connections established via LLM-generated pseudo-queries as edges. During retrieval, it employs a \textit{retrieve-reason-prune} mechanism: starting with lexically or semantically similar passages, the system explores multi-hop neighbors guided by pseudo-queries and LLM reasoning to identify truly relevant ones. Experiments on multiple multi-hop benchmarks demonstrate that HopRAG's \textit{retrieve-reason-prune} mechanism can expand the retrieval scope based on logical connections and improve final answer quality.

**Intro excerpt** (앞 1800자; 전체는 corpus JSON 참고):
> “Everyone and everything is six or fewer steps away, by way of introduction, from any other person in the world.” 

 — Six Degrees of Separation

Retrieval-augmented generation (RAG) has become the standard approach for large language models (LLMs) to tackle knowledge-intensive tasks [cite]. Not only can it effectively address the inherent knowledge limitations and hallucination issues [cite], but it can also enable easy interpretability and provenance tracking [cite]. Especially, the efficacy of RAG hinges on its retrieval module for identifying relevant documents from a vast corpus.

Currently, there are two mainstream types of retrievers: sparse retrievers [cite] and dense retrievers [cite], which focus on lexical similarity and semantic similarity respectively, and are often combined for better retrieval performance [cite].
Despite advancements, the ultimate goal of information retrieval extends beyond lexical and semantic similarity, striving instead for logical relevance. Due to the lack of logic-aware mechanism, the imperfect retrieval remains prominent [cite]. For precision, the retrieval system may return lexically and semantically similar but indirectly relevant passages; regarding recall, it may fail to retrieve all the necessary passages for the user query. 

Both cases eventually lead to inaccurate or incomplete LLM responses [cite], especially for multi-hop or multi-document QA tasks requiring multiple relevant passages for the final answer. 
In contrast, the reasoning capability of generative models is rapidly advancing, with notable examples such as OpenAI-o1 [cite] and DeepSeek-R1 [cite]. Therefore, a natural research question arises: "Is it possible to introduce reasoning capability into the retrieval module for more advanced RAG systems?" 

[Precision

**Suggested framing (EN)**: How does HopRAG handle multi-hop reasoning compared to standard single-step retrieval?
**제안된 방향 (KO)**: HopRAG가 단일 단계 검색과 비교해 multi-hop 추론을 어떻게 다르게 다루는가?

**Q**: [FILL IN]
**GT**: [FILL IN]

### Q8 — paper: `c3788ddba6a255a09eb969b5a8ccd2d5921f53bd`
**Title**: HypRAG: Hyperbolic Dense Retrieval for Retrieval Augmented Generation  (year: 2026)
**arXiv**: <https://arxiv.org/abs/2602.07739>  ·  **full corpus**: `data/corpus/c3788ddba6a255a09eb969b5a8ccd2d5921f53bd.json`

**한글 요약**: HypRAG는 하이퍼볼릭 임베딩 공간에서 dense retrieval을 수행하는 방식 제안.

**Abstract**:
> Embedding geometry plays a fundamental role in retrieval quality, yet dense retrievers for retrieval-augmented generation (RAG) remain largely confined to Euclidean space. However, natural language exhibits hierarchical structure from broad topics to specific entities that Euclidean embeddings fail to preserve, causing semantically distant documents to appear spuriously similar and increasing hallucination risk. To address these limitations, we introduce hyperbolic dense retrieval, developing two model variants in the Lorentz model of hyperbolic space: HyTE-FH, a fully hyperbolic transformer, and HyTE-H, a hybrid architecture projecting pre-trained Euclidean embeddings into hyperbolic space. To prevent representational collapse during sequence aggregation, we introduce the Outward Einstein Midpoint, a geometry-aware pooling operator that provably preserves hierarchical structure. On MTEB, HyTE-FH outperforms equivalent Euclidean baselines, while on RAGBench, HyTE-H achieves up to 29% gains over Euclidean baselines in context relevance and answer relevance using substantially smaller models than current state-of-the-art retrievers. Our analysis also reveals that hyperbolic representations encode document specificity through norm-based separation, with over 20% radial increase from general to specific concepts, a property absent in Euclidean embeddings, underscoring the critical role of geometric inductive bias in faithful RAG systems.

**Intro excerpt** (앞 1800자; 전체는 corpus JSON 참고):
> Dense retrieval forms the backbone of retrieval-augmented generation (RAG) systems [cite], where embedding quality directly determines whether generated responses are grounded in evidence or hallucinated. By retrieving relevant documents and conditioning generation on this context, RAG systems produce responses that are more attributable and aligned with verifiable sources [cite]. Yet, despite advances in retrieval architectures, current systems continue to rely on Euclidean embeddings, a choice inherited from standard neural networks rather than from language structure itself. 

Natural language inherently exhibits strong hierarchical organization [cite], with semantic structure giving rise to locally tree-like neighborhoods. Euclidean spaces struggle to represent such branching hierarchies due to polynomial volume growth [cite], introducing shortcuts between hierarchically distinct regions that distort semantic relationships. 
In retrieval settings, these distortions can cause semantically distant documents to appear spuriously similar [cite], degrading retrieval precision [cite]: a query about a specific subtopic may retrieve documents from sibling or parent categories that share similarity but lack the required specificity.

 
 < g r a p h i c s >

 Hierarchies in Text. (A) Documents naturally organize into branching hierarchies where general topics spawn increasingly specific subtopics. Euclidean spaces distort such hierarchies due to crowding effects, while hyperbolic geometry preserves hierarchical relationships through exponential volume growth. (B) Ricci curvature analysis of document embeddings from strong baselines reveals predominantly negative curvature, indicating tree-like semantic structure.
 

To further see why geometry matters for retrieval, consider 

**Suggested framing (EN)**: How does HypRAG's hyperbolic embedding compare to Euclidean dense retrieval?
**제안된 방향 (KO)**: HypRAG의 hyperbolic 임베딩이 일반적인 Euclidean dense retrieval과 어떻게 다른가?

**Q**: [FILL IN]
**GT**: [FILL IN]

## 3. Multi-hop pairs (3 questions, from 6 papers in pairs)

*Paper A와 Paper B 두 passage가 모두 필요한 질문 하나를 작성하세요. / Write one question that requires BOTH papers' passages to answer.*

### Q9 — papers: `6489640b1d30a8a3e7cb906bb6557f1ccd0d799d` + `e8a9b5a32836af499dcb9ccdee1008638309a6cc`
**Paper A**: Chain-of-Note: Enhancing Robustness in Retrieval-Augmented Language Models  (year: 2023)
**arXiv A**: <https://arxiv.org/abs/2311.09210>  ·  `data/corpus/6489640b1d30a8a3e7cb906bb6557f1ccd0d799d.json`
**한글 요약 A**: Chain-of-Note: 검색된 노트마다 단계별 사고 노트를 생성·검토해 RAG 견고성을 높이는 기법.
> Retrieval-augmented language model (RALM) represents a significant advancement in mitigating factual hallucination by leveraging external knowledge sources. However, the reliability of the retrieved information is not always guaranteed, and the retrieval of irrelevant data can mislead the response generation. Moreover, standard RALMs frequently neglect their intrinsic knowledge due to the interference from retrieved information. In instances where the retrieved information is irrelevant, RALMs should ideally utilize their intrinsic knowledge or, in the absence of both intrinsic and retrieved knowledge, opt to respond with “unknown” to avoid hallucination. In this paper, we introduces Chain-of-Note (CoN), a novel approach to improve robustness of RALMs in facing noisy, irrelevant documents and in handling unknown scenarios. The core idea of CoN is to generate sequential reading notes for each retrieved document, enabling a thorough evaluation of their relevance to the given question and integrating this information to formulate the final answer. Our experimental results show that GPT-4, when equipped with CoN, outperforms the Chain-of-Thought approach. Besides, we utilized GPT-4 to create 10K CoN data, subsequently trained on smaller models like OPT and LLaMa-2. Our experiments across four open-domain QA benchmarks show that fine-tuned RALMs equipped with CoN significantly outperform standard fine-tuned RALMs.

**Paper B**: InstructRAG: Instructing Retrieval-Augmented Generation via Self-Synthesized Rationales  (year: 2024)
**arXiv B**: <https://arxiv.org/abs/2406.13629>  ·  `data/corpus/e8a9b5a32836af499dcb9ccdee1008638309a6cc.json`
**한글 요약 B**: InstructRAG: 검색 결과의 신뢰도를 모델이 스스로 검증·합리화하는 self-synthesized rationale 학습 방식.
> Retrieval-augmented generation (RAG) has shown promising potential to enhance the accuracy and factuality of language models (LMs). However, imperfect retrievers or noisy corpora can introduce misleading or even erroneous information to the retrieved contents, posing a significant challenge to the generation quality. Existing RAG methods typically address this challenge by directly predicting final answers despite potentially noisy inputs, resulting in an implicit denoising process that is difficult to interpret and verify. On the other hand, the acquisition of explicit denoising supervision is often costly, involving significant human efforts. In this work, we propose InstructRAG, where LMs explicitly learn the denoising process through self-synthesized rationales -- First, we instruct the LM to explain how the ground-truth answer is derived from retrieved documents. Then, these rationales can be used either as demonstrations for in-context learning of explicit denoising or as supervised fine-tuning data to train the model. Compared to standard RAG approaches, InstructRAG requires no additional supervision, allows for easier verification of the predicted answers, and effectively improves generation accuracy. Experiments show InstructRAG consistently outperforms existing RAG methods in both training-free and trainable scenarios, achieving a relative improvement of 8.3% over the best baseline method on average across five knowledge-intensive benchmarks. Extensive analysis indicates that InstructRAG scales well with increased numbers of retrieved documents and consistently exhibits robust denoising ability even in out-of-domain datasets, demonstrating strong generalizability.

**Suggested framing (EN)**: How do Chain-of-Note and InstructRAG each try to improve RAG robustness through self-* mechanisms, and how do their approaches differ?
**제안된 방향 (KO)**: Chain-of-Note와 InstructRAG가 self-* 방식으로 RAG 견고성을 높이는 두 방식의 공통점과 차이는?

**Q**: [FILL IN]
**GT**: [FILL IN]

### Q10 — papers: `b63bb769ac924c5411704331071333515b2f5190` + `37845b206ddf48fc757285472159a5198fd320d7`
**Paper A**: Adversarial Hubness Detector: Detecting Hubness Poisoning in Retrieval-Augmented Generation Systems  (year: 2026)
**arXiv A**: <https://arxiv.org/abs/2602.22427>  ·  `data/corpus/b63bb769ac924c5411704331071333515b2f5190.json`
**한글 요약 A**: Adversarial Hubness Detector: RAG 검색기에 hubness poisoning이라는 적대적 공격을 가하고 탐지하는 기법.
> Retrieval-Augmented Generation (RAG) systems are essential to contemporary AI applications, allowing large language models to obtain external knowledge via vector similarity search. Nevertheless, these systems encounter a significant security flaw: hubness - items that frequently appear in the top-$k$ retrieval results for a disproportionately high number of varied queries. These hubs can be exploited to introduce harmful content, alter search rankings, bypass content filtering, and decrease system performance. We introduce hubscan, an open-source security scanner that evaluates vector indices and embeddings to identify hubs in RAG systems. Hubscan presents a multi-detector architecture that integrates: (1) robust statistical hubness detection utilizing median/Median Absolute Deviation (MAD)-based z-scores, (2) cluster spread analysis to assess cross-cluster retrieval patterns, (3) stability testing under query perturbations, and (4) domain-aware and modality-aware detection for category-specific and cross-modal attacks. Our solution accommodates several vector databases (FAISS, Pinecone, Qdrant, Weaviate) and offers versatile retrieval techniques, including vector similarity, hybrid search, and lexical matching with reranking capabilities. We evaluate hubscan on Food-101, MS-COCO, and FiQA adversarial hubness benchmarks constructed using state-of-the-art gradient-optimized and centroid-based hub generation methods. Hubscan achieves 90% recall at a 0.2% alert budget and 100% recall at 0.4%, with adversarial hubs ranking above the 99.8th percentile. In testing, domain-scoped scanning recovered 100% of targeted attacks that evaded global detection. Production validation on 1M real web documents from MS MARCO demonstrates significant score separation between clean documents and adversarial content.

**Paper B**: ProGRank: Probe-Gradient Reranking to Defend Dense-Retriever RAG from Corpus Poisoning  (year: 2026)
**arXiv B**: <https://arxiv.org/abs/2603.22934>  ·  `data/corpus/37845b206ddf48fc757285472159a5198fd320d7.json`
**한글 요약 B**: ProGRank: probe-gradient 기반 리랭킹으로 corpus poisoning을 방어하는 RAG 보안 기법.
> Retrieval-Augmented Generation (RAG) improves the reliability of large language model applications by grounding generation in retrieved evidence, but it also introduces a new attack surface: corpus poisoning. In this setting, an adversary injects or edits passages so that they are ranked into the Top-$K$ results for target queries and then affect downstream generation. Existing defences against corpus poisoning often rely on content filtering, auxiliary models, or generator-side reasoning, which can make deployment more difficult. We propose ProGRank, a post hoc, training-free retriever-side defence for dense-retriever RAG. ProGRank stress-tests each query--passage pair under mild randomized perturbations and extracts probe gradients from a small fixed parameter subset of the retriever. From these signals, it derives two instability signals, representational consistency and dispersion risk, and combines them with a score gate in a reranking step. ProGRank preserves the original passage content, requires no retraining, and also supports a surrogate-based variant when the deployed retriever is unavailable. Extensive experiments across three datasets, three dense retriever backbones, representative corpus poisoning attacks, and both retrieval-stage and end-to-end settings show that ProGRank provides stronger defence performance and a favorable robustness--utility trade-off. It also remains competitive under adaptive evasive attacks.

**Suggested framing (EN)**: What kind of attack does the Adversarial Hubness Detector identify, and how does ProGRank's reranking defense respond to it?
**제안된 방향 (KO)**: Adversarial Hubness Detector가 다루는 공격을 ProGRank의 리랭킹 방어는 어떻게 대응하는가?

**Q**: [FILL IN]
**GT**: [FILL IN]

### Q11 — papers: `2c74686c061a8381f515311aa41b75113019f313` + `226787d438bc47f986f82625d6b74fa6f733ef60`
**Paper A**: MG$^2$-RAG: Multi-Granularity Graph for Multimodal Retrieval-Augmented Generation  (year: 2026)
**arXiv A**: <https://arxiv.org/abs/2604.04969>  ·  `data/corpus/2c74686c061a8381f515311aa41b75113019f313.json`
**한글 요약 A**: MG2-RAG: 다중 granularity 멀티모달 그래프를 활용한 multimodal RAG.
> Retrieval-Augmented Generation (RAG) mitigates hallucinations in Multimodal Large Language Models (MLLMs), yet existing systems struggle with complex cross-modal reasoning. Flat vector retrieval often ignores structural dependencies, while current graph-based methods rely on costly ``translation-to-text''pipelines that discard fine-grained visual information. To address these limitations, we propose \textbf{MG$^2$-RAG}, a lightweight \textbf{M}ulti-\textbf{G}ranularity \textbf{G}raph \textbf{RAG} framework that jointly improves graph construction, modality fusion, and cross-modal retrieval. MG$^2$-RAG constructs a hierarchical multimodal knowledge graph by combining lightweight textual parsing with entity-driven visual grounding, enabling textual entities and visual regions to be fused into unified multimodal nodes that preserve atomic evidence. Building on this representation, we introduce a multi-granularity graph retrieval mechanism that aggregates dense similarities and propagates relevance across the graph to support structured multi-hop reasoning. Extensive experiments across four representative multimodal tasks (i.e., retrieval, knowledge-based VQA, reasoning, and classification) demonstrate that MG$^2$-RAG consistently achieves state-of-the-art performance while reducing graph construction overhead with an average 43.3$\times$ speedup and 23.9$\times$ cost reduction compared with advanced graph-based frameworks.

**Paper B**: M3DocRAG: Multi-modal Retrieval is What You Need for Multi-page Multi-document Understanding  (year: 2024)
**arXiv B**: <https://arxiv.org/abs/2411.04952>  ·  `data/corpus/226787d438bc47f986f82625d6b74fa6f733ef60.json`
**한글 요약 B**: M3DocRAG: 다중 페이지·다중 문서 환경의 멀티모달 RAG.
> Document visual question answering (DocVQA) pipelines that answer questions from documents have broad applications. Existing methods focus on handling single-page documents with multi-modal language models (MLMs), or rely on text-based retrieval-augmented generation (RAG) that uses text extraction tools such as optical character recognition (OCR). However, there are difficulties in applying these methods in real-world scenarios: (a) questions often require information across different pages or documents, where MLMs cannot handle many long documents; (b) documents often have important information in visual elements such as figures, but text extraction tools ignore them. We introduce M3DocRAG, a novel multi-modal RAG framework that flexibly accommodates various document contexts (closed-domain and open-domain), question hops (single-hop and multi-hop), and evidence modalities (text, chart, figure, etc.). M3DocRAG finds relevant documents and answers questions using a multi-modal retriever and an MLM, so that it can efficiently handle single or many documents while preserving visual information. Since previous DocVQA datasets ask questions in the context of a specific document, we also present M3DocVQA, a new benchmark for evaluating open-domain DocVQA over 3,000+ PDF documents with 40,000+ pages. In three benchmarks (M3DocVQA/MMLongBench-Doc/MP-DocVQA), empirical results show that M3DocRAG with ColPali and Qwen2-VL 7B achieves superior performance than many strong baselines, including state-of-the-art performance in MP-DocVQA. We provide comprehensive analyses of different indexing, MLMs, and retrieval models. Lastly, we qualitatively show that M3DocRAG can successfully handle various scenarios, such as when relevant information exists across multiple pages and when answer evidence only exists in images.

**Suggested framing (EN)**: How do MG2-RAG and M3DocRAG differ in the granularity / unit at which they retrieve multimodal evidence?
**제안된 방향 (KO)**: MG2-RAG와 M3DocRAG는 멀티모달 근거를 검색하는 단위/granularity 측면에서 어떻게 다른가?

**Q**: [FILL IN]
**GT**: [FILL IN]

## 4. Methodological (2 questions)

*왜/어떻게 어떤 메커니즘이 작동하는지(인과/과정) 묻는 질문. / Ask why or how a mechanism works (causal/process question).*

### Q12 — paper: `1cc6cc4960f7df59e7813d9a8e11098d0a0d0720`
**Title**: DRAGIN: Dynamic Retrieval Augmented Generation based on the Real-time Information Needs of Large Language Models  (year: 2024)
**arXiv**: <https://arxiv.org/abs/2403.10081>  ·  **full corpus**: `data/corpus/1cc6cc4960f7df59e7813d9a8e11098d0a0d0720.json`

**한글 요약**: DRAGIN은 LLM의 실시간 정보 필요 신호(uncertainty/attention)에 기반해 동적으로 검색을 트리거하는 RAG.

**Abstract**:
> Dynamic retrieval augmented generation (RAG) paradigm actively decides when and what to retrieve during the text generation process of Large Language Models (LLMs). There are two key elements of this paradigm: identifying the optimal moment to activate the retrieval module (deciding when to retrieve) and crafting the appropriate query once retrieval is triggered (determining what to retrieve). However, current dynamic RAG methods fall short in both aspects. Firstly, the strategies for deciding when to retrieve often rely on static rules. Moreover, the strategies for deciding what to retrieve typically limit themselves to the LLM's most recent sentence or the last few tokens, while the LLM's real-time information needs may span across the entire context. To overcome these limitations, we introduce a new framework, DRAGIN, i.e., Dynamic Retrieval Augmented Generation based on the real-time Information Needs of LLMs. Our framework is specifically designed to make decisions on when and what to retrieve based on the LLM's real-time information needs during the text generation process. We evaluate DRAGIN along with existing methods comprehensively over 4 knowledge-intensive generation datasets. Experimental results show that DRAGIN achieves superior performance on all tasks, demonstrating the effectiveness of our method. We have open-sourced all the code, data, and models in GitHub: https://github.com/oneal2000/DRAGIN/tree/main

**Intro excerpt** (앞 1800자; 전체는 corpus JSON 참고):
> In recent years, large language models (LLMs) have made significant advancements across various natural language processing (NLP) tasks, quickly becoming a critical element in numerous AI applications [cite]. Despite their impressive capabilities, these models often produce text that seems coherent and plausible but factually incorrect, a problem commonly known as hallucination [cite].

To mitigate this issue, Retrieval-Augmented Generation (RAG) has emerged as a prominent solution. 
RAG enhances LLMs by retrieving and incorporating relevant information from external databases into the LLMs' inputs. 
It has demonstrated superior effectiveness across numerous NLP challenges [cite]. 
Traditional methods of RAG typically rely on single-round retrieval, using the LLM's initial input to retrieve relevant information from external corpora. 
While this method is effective for straightforward tasks, it tends to fall short for complex multi-step tasks and long-form generation tasks [cite]. 
In contrast, dynamic RAG [cite] performs multiple times of retrieval during the generation process of LLMs. 
It includes two steps: identifying the optimal moment to activate the retrieval module (deciding when to retrieve), and crafting the appropriate query once retrieval is triggered (determining what to retrieve).
Depending on when and what to retrieve, a variety types of methods have been proposed in this direction.
For example, IRCoT [cite] adopts a global augmentation method where retrieval is conducted for each generated sentence, with the latest generated sentence used as the query. 
RETRO [cite] and IC-RALM [cite] define a sliding window and trigger the retrieval module based on a preset number of processed tokens, and the last n tokens are used as the query. 

However, existing dyn

**Suggested framing (EN)**: When does DRAGIN decide to trigger retrieval?
**제안된 방향 (KO)**: DRAGIN은 어떤 신호를 사용해 retrieval을 trigger하는가?

**Q**: [FILL IN]
**GT**: [FILL IN]

### Q13 — paper: `c4aeec57b9ad4fa36cbd9bdad05dbbbd340183df`
**Title**: ARL2: Aligning Retrievers for Black-box Large Language Models via Self-guided Adaptive Relevance Labeling  (year: 2024)
**arXiv**: <https://arxiv.org/abs/2402.13542>  ·  **full corpus**: `data/corpus/c4aeec57b9ad4fa36cbd9bdad05dbbbd340183df.json`

**한글 요약**: ARL2는 black-box LLM과 retriever를 self-guided adaptive relevance labeling으로 정렬하는 학습 방식.

**Abstract**:
> Retrieval-augmented generation enhances large language models (LLMs) by incorporating relevant information from external knowledge sources. This enables LLMs to adapt to specific domains and mitigate hallucinations in knowledge-intensive tasks. However, existing retrievers are often misaligned with LLMs due to their separate training processes and the black-box nature of LLMs. To address this challenge, we propose ARL2, a retriever learning technique that harnesses LLMs as labelers. ARL2 leverages LLMs to annotate and score relevant evidence, enabling learning the retriever from robust LLM supervision. Furthermore, ARL2 uses an adaptive self-training strategy for curating high-quality and diverse relevance data, which can effectively reduce the annotation cost. Extensive experiments demonstrate the effectiveness of ARL2, achieving accuracy improvements of 5.4% on NQ and 4.6% on MMLU compared to the state-of-the-art methods. Additionally, ARL2 exhibits robust transfer learning capabilities and strong zero-shot generalization abilities. Our code will be published at \url{https://github.com/zhanglingxi-cs/ARL2}.

**Intro excerpt** (앞 1800자; 전체는 corpus JSON 참고):
> Retrieval-augmented generation (RAG) is a widely used technique for tailoring large language models (LLMs)
[cite]
to specific domains and tasks.
By incorporating information from external knowledge sources, RAG enhances LLMs by prompting them with relevant evidence [cite], without the need for expensive fine-tuning [cite].
These knowledge sources serve as a non-parametric reference, allowing LLMs to access up-to-date and customized corpora for answering questions.
RAG has shown promising results in improving LLM response accuracy for target tasks, while also helping to mitigate LLM hallucination [cite].

The practice of RAG for state-of-the-art LLMs often involves directly using standard retrievers (e.g. Google Search [cite],
BM25 [cite]) or off-the-shelf dense retrievers (e.g., DPR [cite], Contriever [cite]) trained with supervised relevance signals.
However, the performance of these methods is limited by the mismatch between the retrieval and downstream tasks, as the retrieved similar documents may not always be useful for the queries despite their relevance.
In fact, retrieved documents with similar topics but irrelevant content may even mislead the LLM's predictions [cite].

To address the challenge of adapting retrievers for LLMs, several works propose joint training of retrievers and language models  [cite].
However, these methods require training the LLMs from scratch, which is impractical for cutting-edge LLMs due to their prohibitive training costs and black-box nature.
The recent RePlug method [cite] offers a solution by refining the retriever for black-box LLMs.
RePlug utilizes language modeling scores of the answers as a proxy signal to train the dense retriever.
However, such supervision for retriever training is indirect and may not be discriminative enoug

**Suggested framing (EN)**: What does ARL2 align between retrievers and black-box LLMs?
**제안된 방향 (KO)**: ARL2는 retriever와 black-box LLM 사이에서 무엇을 정렬하는가?

**Q**: [FILL IN]
**GT**: [FILL IN]

## 5. Ambiguous (2 questions)

*넓고 열린 질문. GT는 passage가 뒷받침하는 한도 안에서 '시스템이 이렇게 답하면 충분하다'는 모범 답안을 작성. / Broad/open-ended; GT is the passage-supported answer the system *should* give.*

### Q14 — paper: `45ed289c810d1d7025a2597c66b0e21c592c02a7`
**Title**: Retrieval-Augmented Generation: A Comprehensive Survey of Architectures, Enhancements, and Robustness Frontiers  (year: 2025)
**arXiv**: <https://arxiv.org/abs/2506.00054>  ·  **full corpus**: `data/corpus/45ed289c810d1d7025a2597c66b0e21c592c02a7.json`

**한글 요약**: RAG의 아키텍처·강화기법·평가·응용을 전반적으로 다룬 서베이 논문.

**Abstract**:
> Retrieval-Augmented Generation (RAG) has emerged as a powerful paradigm to enhance large language models (LLMs) by conditioning generation on external evidence retrieved at inference time. While RAG addresses critical limitations of parametric knowledge storage-such as factual inconsistency and domain inflexibility-it introduces new challenges in retrieval quality, grounding fidelity, pipeline efficiency, and robustness against noisy or adversarial inputs. This survey provides a comprehensive synthesis of recent advances in RAG systems, offering a taxonomy that categorizes architectures into retriever-centric, generator-centric, hybrid, and robustness-oriented designs. We systematically analyze enhancements across retrieval optimization, context filtering, decoding control, and efficiency improvements, supported by comparative performance analyses on short-form and multi-hop question answering tasks. Furthermore, we review state-of-the-art evaluation frameworks and benchmarks, highlighting trends in retrieval-aware evaluation, robustness testing, and federated retrieval settings. Our analysis reveals recurring trade-offs between retrieval precision and generation flexibility, efficiency and faithfulness, and modularity and coordination. We conclude by identifying open challenges and future research directions, including adaptive retrieval architectures, real-time retrieval integration, structured reasoning over multi-hop evidence, and privacy-preserving retrieval mechanisms. This survey aims to consolidate current knowledge in RAG research and serve as a foundation for the next generation of retrieval-augmented language modeling systems.

**Intro excerpt** (앞 1800자; 전체는 corpus JSON 참고):
> Large Language Models (LLMs) have demonstrated impressive generalization across natural language tasks, but their reliance on static, parametric knowledge remains a fundamental limitation. This restricts their ability to handle queries requiring up-to-date, verifiable, or domain-specific information, often resulting in hallucinations or factual inconsistencies [cite].

Retrieval-Augmented Generation (RAG) addresses this issue by coupling pretrained language models with non-parametric retrieval modules that fetch external evidence during inference. By conditioning generation on retrieved documents, RAG systems offer greater transparency, factual grounding, and adaptability to evolving knowledge bases. These properties have made RAG central to tasks such as open-domain QA, biomedical reasoning, knowledge-grounded dialogue, and long-context summarization.

However, integrating retrieval with generation introduces unique challenges: retrieval noise and redundancy can degrade output quality; misalignment between retrieved evidence and generated text can lead to hallucinations; and pipeline inefficiencies and latency make deployment costly at scale. Moreover, balancing modularity with tight retrieval–generation interaction remains an open architectural trade-off.

In this survey, we first present a high-level taxonomy of RAG architectures based on where core innovations occur—within the retriever, the generator, or through their joint coordination (Section <ref>). We begin with a background on RAG’s mathematical formulation and components (Section <ref>), and then explore advances in retrieval strategies, filtering, and control mechanisms (Section <ref>). We further analyze how RAG systems are benchmarked (Section <ref>), compare prominent frameworks (Section <ref>), and conc

**Suggested framing (EN)**: How does the survey categorize the architectural variants of RAG?
**제안된 방향 (KO)**: 이 서베이는 RAG 아키텍처를 어떻게 분류·정리하는가?

**Q**: [FILL IN]
**GT**: [FILL IN]

### Q15 — paper: `d48032843bc08c95c0fa71d82818afb34bba55b0`
**Title**: Rethinking Retrieval-Augmented Generation as a Cooperative Decision-Making Problem  (year: 2026)
**arXiv**: <https://arxiv.org/abs/2602.18734>  ·  **full corpus**: `data/corpus/d48032843bc08c95c0fa71d82818afb34bba55b0.json`

**한글 요약**: RAG의 검색기-LLM 상호작용을 협력적 의사결정 문제로 재정식화하는 개념적 프레임워크.

**Abstract**:
> Retrieval-Augmented Generation (RAG) has demonstrated strong effectiveness in knowledge-intensive tasks by grounding language generation in external evidence. Despite its success, many existing RAG systems are built based on a ranking-centric, asymmetric dependency paradigm, where the generation quality of the generator is highly dependent on reranking results of the reranker. To overcome this limitation, we propose Cooperative Retrieval-Augmented Generation (CoRAG), a framework that treats the reranker and the generator as peer decision-makers rather than being connected through an asymmetric dependency pipeline. By jointly optimizing their behaviors toward a shared task objective, the reranker and generator are encouraged to cooperate, ensuring that document reranking and generation work in concert to improve the final response. Experimental results demonstrate good generalization and improved generation stability of CoRAG, even when the model is trained on only around 10K PopQA samples. Our model released in https://github.com/CoderrrSong/CoRAG.

**Intro excerpt** (앞 1800자; 전체는 corpus JSON 참고):
> In recent years, Retrieval-Augmented Generation (RAG) [cite] has emerged as an important paradigm for enhancing the factuality and knowledge coverage of large language models (LLM) [cite]. A typical RAG system consists of two core components: a retriever and a generator [cite]. Given a query, the retriever retrieves candidate documents from a large external corpus and further rerank them via reranker.

The generator then conditions on the query and the reranked documents to produce the final response. By explicitly incorporating external knowledge during generation, RAG effectively mitigates hallucinations and achieves strong performance on open-domain question answering tasks [cite].

 
 < g r a p h i c s >
 
 
 Comparison with previous works.
 Previous works assume an asymmetric dependency between the reranker and the generator, 
 
 whereas CoRAG treats them as equal participants optimized under a shared task-oriented reward.
 
 
 

As the reranker plays a critical role in shaping the document context provided to the generator [cite], a growing body of recent work has focused on the design and optimization of rerankers and generators [cite].

However, most existing RAG methods still adopt a ranking-centric, asymmetric-dependency paradigm (Figure 1(a)), where the reranker produces a fixed document ordering and the generator performs generation conditioned on these top-ranked documents. This design tightly couples generation with reranking decisions, making the generator highly sensitive to the reranking results.

As shown in Figure 1(a), if a suboptimal reranker misranks a less relevant document at the top, the generator may produce an incorrect response, even though the optimal document is still present within the top-N set.

From an optimization perspective, this phe

**Suggested framing (EN)**: Why does the paper frame RAG as a cooperative decision-making problem?
**제안된 방향 (KO)**: 논문은 왜 RAG를 협력적 의사결정 문제로 보는가?

**Q**: [FILL IN]
**GT**: [FILL IN]
