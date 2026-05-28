# External Deployment Checklist

Concrete, ordered steps to take the project from a local repo to public artifacts. Each section is independent — pick the ones that match your goal.

## 1. Discoverability — GitHub Topics

Adds the repo to topic feeds and search. ~30 seconds.

1. Open <https://github.com/parkjongmin-ddam/graphrag-paper>
2. Right sidebar → **About** → ⚙️ → **Topics**
3. Add: `rag`, `graphrag`, `agentic-rag`, `langgraph`, `ragas`, `knowledge-graph`, `dense-retrieval`, `reranker`, `python`
4. Save

## 2. Paper PDF — Overleaf (XeLaTeX)

Produces a citable PDF from `docs/paper.tex`.

1. Open <https://www.overleaf.com> → **New Project** → Upload Project
2. Upload all of `docs/` (`paper.tex`, `references.bib`, `figures/`). Drag-drop the whole folder.
3. Menu → **Compiler** → select **XeLaTeX** (required by `kotex` for the Korean abstract)
4. Click **Recompile**. Overleaf auto-runs `bibtex` for citations.
5. Edit `\author{[Your Name]}` in `paper.tex` line 22 with your name/affiliation
6. **Download PDF** → drop into `docs/paper.pdf` (commit)
7. Optional: update `README.md` badge to link to the PDF instead of the LaTeX source.

## 3. arXiv Submission (optional)

Only do this if you want a citable arXiv ID. Requires the compiled PDF from step 2.

1. Create / log in at <https://arxiv.org/user/>
2. **Submit a new article** → category `cs.IR` (primary) + `cs.CL` (cross-list)
3. **Upload**: zip the Overleaf source (Menu → Download → Source) and upload the zip. arXiv compiles it on their side.
4. Title/abstract: copy from `paper.tex` `\title{}` and `\begin{abstract}` block
5. **License**: arXiv permissive license is fine (CC-BY 4.0 recommended for max reuse)
6. **Preview** the auto-generated PDF, fix any compile errors, submit
7. After acceptance (usually <1 business day), add the arXiv link to the README and the BLOG

## 4. Streamlit Demo — Hugging Face Spaces

Public interactive demo. ~15 minutes the first time.

### Prereqs

- A Hugging Face account: <https://huggingface.co/join>
- An Anthropic API key (the demo calls Claude for the agent's LLM nodes)

### Steps

1. <https://huggingface.co/new-space> → choose **Streamlit** SDK, hardware **CPU basic** (free), set space name `graphrag-paper-demo`, visibility **Public**
2. The new Space gives you a git URL. Clone it:
   ```bash
   git clone https://huggingface.co/spaces/<your-user>/graphrag-paper-demo
   ```
3. Copy these from the main repo into the Space repo root:
   - `demo/app.py` → rename to `app.py` (HF Spaces convention)
   - The entire `core/`, `agent/`, `search/`, `eval/`, `graph/`, `ingest/` directories
   - `requirements.txt` (concat the contents of `demo/requirements.txt` into it)
   - `data/graph/knowledge_graph.json`
   - `data/corpus/` (all 100 JSON files)
   - `data/eval/questions.json` (optional, for example questions)
4. **Vector index** is 19 MB — too large to commit comfortably. Two options:
   - **Recommended**: regenerate on first Space start. Add a small `setup.py` (or run in `app.py` startup) that calls `BuildVectorIndexStage().run(cfg)` if `data/vector/` is empty. Takes ~30s on Space cold start.
   - Or use Git LFS for `data/vector/`.
5. **Secrets**: Space → Settings → **Repository secrets** → add `ANTHROPIC_API_KEY`. The Space exposes it as an env var that `core/config.py` reads via `python-dotenv`/`os.environ`.
6. `git push` to the Space — it auto-builds and starts.
7. Once running, link the Space from `README.md` (live demo badge).

### Caveats

- The free Space sleeps after inactivity; first request after sleep takes 30–60s.
- Every demo question costs a few cents of Anthropic API. Consider rate-limiting or restricting to a fixed example set if you expect significant traffic.

## 5. Blog Publishing

`docs/BLOG.md` is written in plain Markdown — most platforms accept it.

| Platform | How |
|---|---|
| **dev.to** | New post → paste BLOG.md. Adjust image links to absolute GitHub `raw.githubusercontent.com` URLs. Add tags `rag`, `llm`, `langchain`. |
| **Medium** | Paste BLOG.md; Medium handles most Markdown. Images must be uploaded (drag-drop). |
| **Personal blog (MDX / Jekyll / Hugo)** | Copy file in; replace relative `figures/...` paths with your site's image hosting. |
| **LinkedIn Articles** | Paste plain text; LinkedIn renders headings and lists but not tables — replace tables with bullet summaries. |

After publishing, add the link to the top of `README.md` (e.g., `**Blog post**: <url>`) and to `docs/BLOG.md` footer.

## 6. Pin to your GitHub profile

1. Open <https://github.com/parkjongmin-ddam>
2. **Customize your pins** → check `graphrag-paper`
3. Save. The repo now appears on your profile.

## Final state

After all of the above:

- ✅ Repo discoverable via topics
- ✅ Compiled PDF in repo (optionally on arXiv)
- ✅ Live interactive demo on HF Spaces
- ✅ Readable blog post indexed by Google
- ✅ Pinned on your GitHub profile

README badges to add as you go: blog link, arXiv badge (`https://img.shields.io/badge/arXiv-XXXX.XXXXX-b31b1b`), HF Spaces badge (`https://img.shields.io/badge/🤗_Spaces-demo-yellow`).
