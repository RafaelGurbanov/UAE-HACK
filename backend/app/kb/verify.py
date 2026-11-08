"""Citation verification. Runs after generation and never trusts the model:

- every [cN] marker in the text must be defined in the citations block;
- every citation must point to a source that was actually retrieved;
- every quote must be an exact substring of that source's text
  (after normalize_for_match) and at least 12 characters long.

Failing citations are removed, their markers stripped from the text, and the
removal is reported. `passed` is True only when at least one citation survives
and none failed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.kb.text import normalize_for_match

MIN_QUOTE = 12


@dataclass
class RawCitation:
    cid: str          # "c1"
    source: int       # 1-based index into the retrieved sources ("S3" -> 3)
    quote: str


@dataclass
class CheckedCitation:
    raw: RawCitation
    chunk: dict
    score: float
    verified: bool
    reason: str | None = None


_LINE = re.compile(r"^\s*\[?(c\d+)\]?\s*[:\-]?\s*S(\d+)\s*\|\s*(.+?)\s*$", re.I)
_MARKER = re.compile(r"\[(c\d+)\]")


def parse_citations(block: str) -> list[RawCitation]:
    out, seen = [], set()
    for line in block.splitlines():
        m = _LINE.match(line)
        if not m:
            continue
        cid = m.group(1).lower()
        if cid in seen:
            continue
        seen.add(cid)
        quote = m.group(3).strip().strip('"“”«»').strip()
        out.append(RawCitation(cid=cid, source=int(m.group(2)), quote=quote))
    return out


def check(citations: list[RawCitation], sources: list[tuple[dict, float]]) -> list[CheckedCitation]:
    out = []
    for c in citations:
        if not 1 <= c.source <= len(sources):
            out.append(CheckedCitation(c, {}, 0.0, False, f"{c.cid}: cites S{c.source}, which was not retrieved"))
            continue
        chunk, score = sources[c.source - 1]
        q = normalize_for_match(c.quote)
        if len(q) < MIN_QUOTE:
            out.append(CheckedCitation(c, chunk, score, False, f"{c.cid}: quote too short to verify"))
        elif q not in normalize_for_match(chunk["text"]):
            out.append(CheckedCitation(c, chunk, score, False, f"{c.cid}: quote not found in S{c.source}"))
        else:
            out.append(CheckedCitation(c, chunk, score, True))
    return out


def strip_markers(text: str, keep: set[str]) -> tuple[str, list[str]]:
    """Remove markers not in `keep`; return the new text and the removed marker ids."""
    removed: list[str] = []

    def sub(m: re.Match) -> str:
        if m.group(1).lower() in keep:
            return m.group(0)
        removed.append(m.group(1))
        return ""

    new = _MARKER.sub(sub, text or "")
    return re.sub(r"\s+([.,;:،؛])", r"\1", re.sub(r"[ \t]{2,}", " ", new)).strip(), removed


def markers_in(text: str) -> set[str]:
    return {m.lower() for m in _MARKER.findall(text or "")}
