"""
GraphRAG-Paper - Parse human-authored questions draft
--------------------------------------------------
Reads docs/questions_human_draft.md (filled in by a human reviewer) and writes
data/eval/questions_human.json in the same shape as questions.json.

Schema per item:
  {
    "question":         "...",
    "ground_truth":     "...",
    "source_paper_id":  "<primary paper_id>",
    "source_paper_ids": ["<a>", "<b>"],   # present for multi-hop pairs
    "category":         "fact|compare|multihop|method|ambig"
  }

Entries that still contain [FILL IN] are SKIPPED with a warning, so a partially
filled draft is still usable (the downstream eval just runs on n_filled).

Run from project root:
    python -m eval.parse_human_draft
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

DRAFT_PATH = Path("docs/questions_human_draft.md")
OUT_PATH = Path("data/eval/questions_human.json")

# Category headers in the draft → category tag
CATEGORY_HEADERS = [
    ("Fact-specific", "fact"),
    ("Comparative", "compare"),
    ("Multi-hop pairs", "multihop"),
    ("Methodological", "method"),
    ("Ambiguous", "ambig"),
]

PLACEHOLDER = "[FILL IN]"
HEADER_RE = re.compile(
    r"^### Q(\d+)\s+—\s+papers?:\s+`([a-f0-9]{40})`(?:\s*\+\s*`([a-f0-9]{40})`)?",
)
Q_RE = re.compile(r"^\*\*Q\*\*:\s*(.+)$")
GT_RE = re.compile(r"^\*\*GT\*\*:\s*(.+)$")

log = logging.getLogger("parse_human")


def _detect_category(line: str) -> str | None:
    """Match a markdown H2 header line (## N. <Name>) to a category tag."""
    if not line.startswith("## "):
        return None
    for needle, tag in CATEGORY_HEADERS:
        if needle in line:
            return tag
    return None


def parse(draft_text: str) -> list[dict]:
    """Split the draft into Q blocks, extract (paper_ids, Q, GT) for each filled one."""
    lines = draft_text.splitlines()
    current_category: str | None = None
    items: list[dict] = []
    skipped: list[int] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        cat = _detect_category(line)
        if cat:
            current_category = cat
            i += 1
            continue
        header = HEADER_RE.match(line)
        if not header:
            i += 1
            continue
        qnum = int(header.group(1))
        pid_a = header.group(2)
        pid_b = header.group(3)  # None for single-paper questions

        # Scan forward for Q and GT lines (within this block, before the next ###)
        q_text: str | None = None
        gt_text: str | None = None
        j = i + 1
        while j < len(lines) and not lines[j].startswith("### Q"):
            m_q = Q_RE.match(lines[j])
            m_gt = GT_RE.match(lines[j])
            if m_q and q_text is None:
                q_text = m_q.group(1).strip()
            elif m_gt and gt_text is None:
                gt_text = m_gt.group(1).strip()
            j += 1

        if q_text is None or gt_text is None:
            log.warning("Q%d: missing Q or GT — skipped", qnum)
            skipped.append(qnum)
        elif PLACEHOLDER in q_text or PLACEHOLDER in gt_text or not q_text or not gt_text:
            log.info("Q%d: still has %s — skipped", qnum, PLACEHOLDER)
            skipped.append(qnum)
        else:
            item: dict = {
                "question": q_text,
                "ground_truth": gt_text,
                "source_paper_id": pid_a,
                "category": current_category or "unknown",
            }
            if pid_b is not None:
                item["source_paper_ids"] = [pid_a, pid_b]
                if not current_category:
                    item["category"] = "multihop"
            items.append(item)
        i = j

    if skipped:
        log.info("skipped %d/%d unfilled questions: %s",
                 len(skipped), len(items) + len(skipped), skipped)
    return items


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not DRAFT_PATH.exists():
        log.error("%s not found — generate the draft first", DRAFT_PATH)
        sys.exit(1)
    text = DRAFT_PATH.read_text(encoding="utf-8")
    items = parse(text)
    if not items:
        log.error("no filled questions found in %s", DRAFT_PATH)
        sys.exit(1)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("wrote %s (%d questions)", OUT_PATH, len(items))
    by_cat: dict[str, int] = {}
    for it in items:
        by_cat[it.get("category", "?")] = by_cat.get(it.get("category", "?"), 0) + 1
    log.info("by category: %s", by_cat)


if __name__ == "__main__":
    main()
