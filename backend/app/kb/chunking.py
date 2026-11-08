"""Parse PDF / HTML / TXT and chunk by Law > Chapter > Article.

One chunk per article; long articles are split into parts that keep the
article number. Documents with no detectable articles fall back to
paragraph-window chunks (article = None) so they are still searchable.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from app.kb.text import to_ascii_digits

log = logging.getLogger(__name__)

SUPPORTED = {".pdf", ".html", ".htm", ".txt", ".md"}
MAX_CHARS = 2000      # split articles longer than this
PART_CHARS = 1500     # target size of each part
FALLBACK_CHARS = 1200  # paragraph-window size when no articles are found

# "Article 5", "ARTICLE (5)", "Art. 12a", "Article V"
_EN_ARTICLE = re.compile(
    r"^\s*(?:Article|ARTICLE|Art\.)\s*\(?\s*(\d+[A-Za-z]?|[IVXLC]{1,6})\s*\)?\s*(?:[:.\-–]\s*)?(.{0,120})$"
)
# "المادة (5)", "مادة 5", "المادة الأولى", "المادة الحادية عشرة"
_AR_ARTICLE = re.compile(
    r"^\s*(?:ال)?ماد[ةه]\s*\(?\s*([0-9٠-٩]+|[ء-ي]+(?:\s+[ء-ي]+){0,2})\s*\)?\s*(?:[:.\-–]\s*)?(.{0,120})$"
)
_EN_CHAPTER = re.compile(r"^\s*(Chapter|CHAPTER|Part|PART|Title|TITLE|Section|SECTION)\s+([\w\-]+)\b(.{0,120})$")
_AR_CHAPTER = re.compile(r"^\s*(الفصل|الباب|الفرع|القسم)\s+(.{1,80})$")


@dataclass
class Segment:
    article: str | None
    heading: str | None
    chapter: str | None
    text: str


# ---------------------------------------------------------------- parsing
def parse_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _parse_pdf(path)
    if ext in {".html", ".htm"}:
        return _parse_html(path.read_bytes())
    return path.read_text(encoding="utf-8", errors="replace")


def _parse_pdf(path: Path) -> str:
    import pymupdf

    pages: list[list[str]] = []
    with pymupdf.open(str(path)) as doc:
        for page in doc:
            lines = [ln.rstrip() for ln in page.get_text("text", sort=True).splitlines()]
            pages.append(lines)
    # drop running headers/footers: short lines repeated on > 50% of pages
    if len(pages) >= 4:
        counts = Counter(ln.strip() for pg in pages for ln in set(pg) if 0 < len(ln.strip()) < 80)
        repeated = {ln for ln, n in counts.items() if n > len(pages) * 0.5 and not re.search(r"\d{3,}", ln)}
        pages = [[ln for ln in pg if ln.strip() not in repeated] for pg in pages]
    text = "\n".join("\n".join(pg) for pg in pages)
    if len(text.strip()) < 200:
        log.warning("%s: very little text extracted (scanned PDF? needs OCR)", path.name)
    return text


def _parse_html(raw: bytes) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "form"]):
        tag.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    return root.get_text("\n")


# ---------------------------------------------------------------- chunking
def _clean(text: str) -> str:
    text = text.replace("\r", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def _num(label: str) -> int | None:
    lab = to_ascii_digits(label).strip()
    m = re.match(r"^(\d+)", lab)
    if m:
        return int(m.group(1))
    if re.fullmatch(r"[IVXLC]+", lab):
        total, prev = 0, 0
        for ch in reversed(lab):
            v = _ROMAN[ch]
            total, prev = (total - v, prev) if v < prev else (total + v, v)
        return total
    return None


def split_articles(text: str) -> list[Segment]:
    text = _clean(text)
    lines = text.split("\n")
    segs: list[Segment] = []
    cur = Segment(None, "Preamble", None, "")
    chapter: str | None = None
    last_num = 0
    buf: list[str] = []

    def flush():
        cur.text = "\n".join(buf).strip()
        if cur.text:
            segs.append(cur)

    for ln in lines:
        s = ln.strip()
        ch = _EN_CHAPTER.match(s) or _AR_CHAPTER.match(s)
        if ch and len(s) < 120:
            chapter = s
        m = _EN_ARTICLE.match(s) or _AR_ARTICLE.match(s)
        if m and len(s) < 140:
            label = to_ascii_digits(m.group(1)).strip()
            n = _num(label)
            # guard against in-text references ("Article 3 of this Law") restarting numbering
            if n is None or n >= last_num:
                flush()
                last_num = n if n is not None else last_num
                heading = (m.group(2) or "").strip() or None
                cur = Segment(label, heading, chapter, "")
                buf = [s]
                continue
        buf.append(ln)
    flush()
    return segs


def _split_long(text: str) -> list[str]:
    if len(text) <= MAX_CHARS:
        return [text]
    paras = re.split(r"\n\s*\n|\n(?=\s*(?:\(?\d+[.)]|\(?[a-z][.)]|[-•]))", text)
    parts, cur = [], ""
    for p in paras:
        if len(cur) + len(p) > PART_CHARS and cur:
            parts.append(cur.strip())
            cur = ""
        while len(p) > MAX_CHARS:  # one giant paragraph: hard split on sentence boundary
            cut = p.rfind(". ", 0, PART_CHARS)
            cut = cut + 1 if cut > 200 else PART_CHARS
            parts.append(p[:cut].strip())
            p = p[cut:]
        cur += ("\n\n" if cur else "") + p
    if cur.strip():
        parts.append(cur.strip())
    return parts


def chunk_document(text: str) -> tuple[list[dict], int]:
    """Returns (chunks without metadata, number of articles detected)."""
    segs = split_articles(text)
    articles = sum(1 for s in segs if s.article)
    out: list[dict] = []
    if articles >= 2:
        for s in segs:
            parts = _split_long(s.text)
            for i, part in enumerate(parts):
                out.append({"article": s.article, "heading": s.heading, "chapter": s.chapter,
                            "part": i if len(parts) > 1 else None, "text": part})
    else:  # no article structure: paragraph windows
        paras = [p.strip() for p in re.split(r"\n\s*\n", _clean(text)) if p.strip()]
        cur, n = "", 0
        for p in paras:
            if len(cur) + len(p) > FALLBACK_CHARS and cur:
                n += 1
                out.append({"article": None, "heading": f"Section {n}", "chapter": None, "part": None, "text": cur})
                cur = ""
            cur += ("\n\n" if cur else "") + p
        if cur:
            n += 1
            out.append({"article": None, "heading": f"Section {n}", "chapter": None, "part": None, "text": cur})
        # a single huge paragraph can still exceed the limit: split it
        out = [
            {**c, "part": i if len(pieces) > 1 else None, "text": piece}
            for c in out
            for pieces in [_split_long(c["text"])]
            for i, piece in enumerate(pieces)
        ]
        articles = 0
    return [c for c in out if len(c["text"]) >= 20], articles
