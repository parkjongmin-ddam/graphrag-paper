"""
GraphRAG-Paper - A-M0 - extract_sections.py
--------------------------------------------------
For each arXiv ID in paper_list.json, fetch the LaTeX source and extract the
Introduction / Related Work sections. Falls back to GROBID PDF parsing when
GROBID_URL is set, and finally to abstract_only when both paths fail.

Output: data/raw/<arxiv_id>.json (one RawSections per paper).
"""

from __future__ import annotations

import gzip
import io
import logging
import os
import re
import tarfile
import tempfile
import time
from pathlib import Path
from xml.etree import ElementTree as ET

from core.artifacts import load_paper_list, write_json
from core.config import PipelineConfig
from core.schemas import PaperRef, RawSections
from core.stage import Stage, StageReport

# ----------------------------- constants -----------------------------
ARXIV_EPRINT_URL = "https://arxiv.org/e-print/{aid}"
ARXIV_PDF_URL = "https://arxiv.org/pdf/{aid}.pdf"

SLEEP_SEC = 3.0  # arXiv asks for >= 3s between automated calls
TIMEOUT_SEC = 60
MAX_RETRY = 3
USER_AGENT = "graphrag-paper/0.1 (research; mailto:jongminoov@gmail.com)"

GROBID_ENDPOINT = "/api/processFulltextDocument"

INTRO_KEYS = ("introduction",)
RELATED_KEYS = ("related work", "related works", "related-work", "background")

_TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}

log = logging.getLogger("extract_sections")


# ----------------------------- HTTP -----------------------------
def _http_get(url: str):
    """GET with retry on 429/5xx (lazy requests import keeps the harness lightweight)."""
    import requests

    headers = {"User-Agent": USER_AGENT}
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRY):
        try:
            resp = requests.get(url, headers=headers, timeout=TIMEOUT_SEC)
            if resp.status_code == 200:
                return resp
            if resp.status_code in (429, 500, 502, 503):
                time.sleep(SLEEP_SEC * (2 ** attempt))
                continue
            resp.raise_for_status()
        except requests.RequestException as e:
            last_exc = e
            time.sleep(SLEEP_SEC * (2 ** attempt))
    raise RuntimeError(f"GET failed: {url} ({last_exc})")


# ----------------------------- arXiv e-print -----------------------------
def _download_eprint(arxiv_id: str, dest: Path) -> str | None:
    """Save the e-print; return content kind ('tar' | 'gz_tex' | 'pdf' | None)."""
    resp = _http_get(ARXIV_EPRINT_URL.format(aid=arxiv_id))
    raw = resp.content
    dest.write_bytes(raw)

    if raw[:5] == b"%PDF-":
        return "pdf"
    if raw[:2] == b"\x1f\x8b":
        try:
            with gzip.open(io.BytesIO(raw), "rb") as g:
                head = g.read(512)
            # ustar magic lives at offset 257 inside a tar archive
            if len(head) >= 263 and head[257:262] == b"ustar":
                return "tar"
            return "gz_tex"
        except OSError:
            return None
    return None


def _extract_archive(eprint_path: Path, kind: str, work_dir: Path) -> Path | None:
    """Unpack e-print into work_dir and return the path to the main .tex."""
    work_dir.mkdir(parents=True, exist_ok=True)
    if kind == "tar":
        try:
            with tarfile.open(eprint_path, "r:gz") as tar:
                safe = [
                    m for m in tar.getmembers()
                    if not (m.name.startswith("/") or ".." in Path(m.name).parts)
                ]
                tar.extractall(work_dir, members=safe)
        except tarfile.TarError as e:
            log.warning("tar extract failed: %s", e)
            return None
        return _find_main_tex(work_dir)

    if kind == "gz_tex":
        try:
            with gzip.open(eprint_path, "rb") as g:
                content = g.read()
        except OSError as e:
            log.warning("gz extract failed: %s", e)
            return None
        out = work_dir / "main.tex"
        out.write_bytes(content)
        return out

    return None


def _find_main_tex(work_dir: Path) -> Path | None:
    tex_files = list(work_dir.rglob("*.tex"))
    if not tex_files:
        return None
    for tex in tex_files:
        try:
            head = tex.read_text(encoding="utf-8", errors="ignore")[:4000]
        except OSError:
            continue
        if r"\documentclass" in head:
            return tex
    return max(tex_files, key=lambda p: p.stat().st_size)


# ----------------------------- LaTeX parsing -----------------------------
_COMMENT_RE = re.compile(r"(?<!\\)%.*?$", re.MULTILINE)
_INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")
_SECTION_RE = re.compile(r"\\(section|chapter)\*?\s*\{(?P<title>[^}]*)\}", re.IGNORECASE)
_BIB_RE = re.compile(
    r"\\(bibliography|printbibliography|begin\{thebibliography\})", re.IGNORECASE
)
_TITLE_CMD_RE = re.compile(r"\\[a-zA-Z]+\*?\s*\{([^{}]*)\}")


def _strip_comments(latex: str) -> str:
    return _COMMENT_RE.sub("", latex)


def _expand_inputs(main_tex: Path, max_depth: int = 4) -> str:
    """Inline \\input{x} and \\include{x} relative to main_tex's directory."""
    base = main_tex.parent
    seen: set[Path] = set()

    def _read(path: Path, depth: int) -> str:
        if depth > max_depth or path in seen:
            return ""
        seen.add(path)
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""
        text = _strip_comments(text)

        def _replace(m: re.Match) -> str:
            target = m.group(1).strip()
            tp = Path(target)
            cand = base / (tp.with_suffix(".tex") if not tp.suffix else tp)
            if cand.exists() and cand.is_file():
                return "\n" + _read(cand, depth + 1) + "\n"
            return ""

        return _INPUT_RE.sub(_replace, text)

    return _read(main_tex, 0)


def split_sections(latex: str) -> dict[str, str]:
    """Locate intro / related_work LaTeX chunks by top-level section boundary."""
    m = re.search(r"\\begin\s*\{document\}", latex)
    body = latex[m.end():] if m else latex

    mbib = _BIB_RE.search(body)
    if mbib:
        body = body[: mbib.start()]

    matches = list(_SECTION_RE.finditer(body))
    out: dict[str, str] = {}
    for i, mm in enumerate(matches):
        title = _TITLE_CMD_RE.sub(r"\1", mm.group("title")).strip().lower()
        start = mm.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        chunk = body[start:end]
        if any(k in title for k in INTRO_KEYS) and "intro" not in out:
            out["intro"] = chunk
        elif any(k in title for k in RELATED_KEYS) and "related_work" not in out:
            out["related_work"] = chunk
    return out


def latex_to_text(latex: str) -> str:
    """LaTeX -> plain text via pylatexenc."""
    from pylatexenc.latex2text import LatexNodes2Text
    return LatexNodes2Text().latex_to_text(latex).strip()


# ----------------------------- GROBID fallback -----------------------------
def _download_pdf(arxiv_id: str, dest: Path) -> bool:
    try:
        resp = _http_get(ARXIV_PDF_URL.format(aid=arxiv_id))
    except RuntimeError as e:
        log.warning("PDF download failed %s: %s", arxiv_id, e)
        return False
    if not resp.content.startswith(b"%PDF-"):
        log.warning("non-PDF response for %s", arxiv_id)
        return False
    dest.write_bytes(resp.content)
    return True


def _grobid_extract(pdf_path: Path, grobid_url: str) -> dict[str, str] | None:
    """POST PDF to GROBID, parse TEI, return {intro?, related_work?}."""
    import requests

    url = f"{grobid_url.rstrip('/')}{GROBID_ENDPOINT}"
    try:
        with pdf_path.open("rb") as f:
            resp = requests.post(
                url,
                files={"input": (pdf_path.name, f, "application/pdf")},
                data={"consolidateHeader": "0", "consolidateCitations": "0"},
                timeout=TIMEOUT_SEC * 2,
                headers={"User-Agent": USER_AGENT},
            )
    except requests.RequestException as e:
        log.warning("GROBID request failed: %s", e)
        return None
    if resp.status_code != 200:
        log.warning("GROBID status %s", resp.status_code)
        return None
    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        log.warning("TEI parse failed: %s", e)
        return None

    out: dict[str, str] = {}
    for div in root.findall(".//tei:body/tei:div", _TEI_NS):
        head = div.find("tei:head", _TEI_NS)
        title = (head.text or "").strip().lower() if head is not None else ""
        body_text = _tei_text(div, skip_head=True)
        if not body_text:
            continue
        if any(k in title for k in INTRO_KEYS) and "intro" not in out:
            out["intro"] = body_text
        elif any(k in title for k in RELATED_KEYS) and "related_work" not in out:
            out["related_work"] = body_text
    return out or None


def _tei_text(el: ET.Element, skip_head: bool = False) -> str:
    parts: list[str] = []
    for node in el.iter():
        tag = node.tag.split("}", 1)[-1]
        if skip_head and tag == "head":
            continue
        if node.text:
            parts.append(node.text)
        if node.tail:
            parts.append(node.tail)
    return re.sub(r"[ \t]+", " ", " ".join(parts)).strip()


# ----------------------------- per-paper pipeline -----------------------------
def _safe_aid(arxiv_id: str) -> str:
    return arxiv_id.replace("/", "_")


def _process_paper(paper: PaperRef, work_root: Path, grobid_url: str | None) -> RawSections | None:
    arxiv_id = paper.arxiv_id
    if not arxiv_id:
        return None

    safe = _safe_aid(arxiv_id)
    with tempfile.TemporaryDirectory(prefix=f"eprint_{safe}_", dir=work_root) as tmp:
        tmp_path = Path(tmp)
        eprint_path = tmp_path / f"{safe}.eprint"

        try:
            kind = _download_eprint(arxiv_id, eprint_path)
        except RuntimeError as e:
            log.warning("e-print failed %s: %s", arxiv_id, e)
            kind = None

        intro = ""
        related = ""
        source = "abstract_only"

        if kind in ("tar", "gz_tex"):
            main_tex = _extract_archive(eprint_path, kind, tmp_path / "src")
            if main_tex is not None:
                latex = _expand_inputs(main_tex)
                sections = split_sections(latex)
                if "intro" in sections:
                    try:
                        intro = latex_to_text(sections["intro"])
                    except Exception as e:  # pylatexenc occasionally chokes on macros
                        log.warning("intro LaTeX parse failed for %s: %s", arxiv_id, e)
                if "related_work" in sections:
                    try:
                        related = latex_to_text(sections["related_work"])
                    except Exception as e:
                        log.warning("related_work LaTeX parse failed for %s: %s", arxiv_id, e)
                if intro or related:
                    source = "latex"

        if source != "latex" and grobid_url:
            pdf_path = tmp_path / f"{safe}.pdf"
            if kind == "pdf":
                eprint_path.rename(pdf_path)
                pdf_ok = True
            else:
                pdf_ok = _download_pdf(arxiv_id, pdf_path)
            if pdf_ok:
                grobid = _grobid_extract(pdf_path, grobid_url)
                if grobid:
                    intro = intro or grobid.get("intro", "")
                    related = related or grobid.get("related_work", "")
                    if intro or related:
                        source = "grobid"

    return RawSections(
        arxiv_id=arxiv_id,
        abstract=paper.abstract or "",
        intro=intro,
        related_work=related,
        source=source,  # type: ignore[arg-type]
    )


# ----------------------------- main -----------------------------
def extract_sections(config: PipelineConfig) -> list[RawSections]:
    """Read paper_list, fetch+parse sections, write data/raw/*.json, return them.

    Assumes data/paper_list.json exists (the stage gates on this).
    Makes live arXiv calls; the stage also gates on config.allow_network.
    """
    papers = load_paper_list(config)
    config.raw_dir.mkdir(parents=True, exist_ok=True)
    grobid_url = os.environ.get("GROBID_URL")
    if not grobid_url:
        log.info("GROBID_URL unset; PDF fallback disabled (latex-or-abstract_only)")

    results: list[RawSections] = []
    with tempfile.TemporaryDirectory(prefix="graphrag_extract_") as work_root:
        work_root_path = Path(work_root)
        for i, paper in enumerate(papers, 1):
            if not paper.arxiv_id:
                log.info("[%d/%d] no arxiv_id, skipping %s", i, len(papers), paper.paper_id)
                continue
            out_path = config.raw_dir / f"{_safe_aid(paper.arxiv_id)}.json"
            if out_path.exists() and not config.force:
                log.info("[%d/%d] %s already extracted", i, len(papers), paper.arxiv_id)
                continue
            try:
                result = _process_paper(paper, work_root_path, grobid_url)
            except Exception as e:
                log.exception("[%d/%d] %s failed: %s", i, len(papers), paper.arxiv_id, e)
                continue
            if result is None:
                continue
            write_json(out_path, result)
            results.append(result)
            log.info(
                "[%d/%d] %s [%s] intro=%s related=%s",
                i, len(papers), paper.arxiv_id, result.source,
                "Y" if result.intro else "N",
                "Y" if result.related_work else "N",
            )
            time.sleep(SLEEP_SEC)
    return results


class ExtractSectionsStage(Stage):
    name = "extract_sections"
    milestone = "A-M0"
    requires = ("collect",)

    def run(self, config: PipelineConfig) -> StageReport:
        papers = load_paper_list(config)
        if not papers:
            return self.skipped("no paper_list.json (run collect first)")
        if not config.allow_network:
            return self.skipped(
                "network gated; pass --allow-network or set GRAPHRAG_ALLOW_NETWORK=1"
            )
        sections = extract_sections(config)
        return self.ok(outputs=(config.raw_dir,), papers=len(papers), sections=len(sections))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from core.pipeline import PipelineRunner
    PipelineRunner([ExtractSectionsStage()]).run(PipelineConfig.from_env())


if __name__ == "__main__":
    main()
