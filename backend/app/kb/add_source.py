"""Download a document into kb/raw and register it in kb/sources.csv.

    python -m app.kb.add_source <url> --title "..." --layer uae_federal [--language ar]
        [--issuing-body "..."] [--law-number "..."] [--year 2021] [--status in_force]
        [--domains "children_data;consent"] [--translation-of <doc_id>] [--doc-id <id>]

Only use official URLs you have checked. The row is saved with verified=false;
set it to true in sources.csv after checking the file against the official source.
Then run: python -m app.kb.ingest
"""

from __future__ import annotations

import argparse
import mimetypes
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.kb.registry import LAYERS, STATUSES, append_row, read_rows, slugify

EXT_BY_TYPE = {"application/pdf": ".pdf", "text/html": ".html", "application/xhtml+xml": ".html", "text/plain": ".txt"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--title", required=True)
    ap.add_argument("--layer", required=True, choices=sorted(LAYERS))
    ap.add_argument("--language", default="ar", choices=["ar", "en"])
    ap.add_argument("--issuing-body", default="")
    ap.add_argument("--law-number", default="")
    ap.add_argument("--year", default="")
    ap.add_argument("--status", default="unknown", choices=sorted(STATUSES))
    ap.add_argument("--domains", default="", help="semicolon-separated, e.g. children_data;consent")
    ap.add_argument("--translation-of", default="", help="doc_id of the Arabic original")
    ap.add_argument("--doc-id", default="")
    ap.add_argument("--force", action="store_true", help="overwrite an existing doc_id")
    a = ap.parse_args(argv)

    if urlparse(a.url).scheme not in {"http", "https"}:
        print("URL must start with http:// or https://", file=sys.stderr)
        return 2
    kb = get_settings().kb_dir
    doc_id = a.doc_id or f"{slugify(a.title, 50)}-{a.language}"
    if doc_id in {r["doc_id"] for r in read_rows(kb)} and not a.force:
        print(f"doc_id '{doc_id}' already exists in sources.csv (use --doc-id or --force)", file=sys.stderr)
        return 3

    print(f"Downloading {a.url} ...")
    with httpx.Client(follow_redirects=True, timeout=120, headers={"User-Agent": "Mozilla/5.0 (KB ingest)"}) as c:
        r = c.get(a.url)
    if r.status_code != 200:
        print(f"Download failed: HTTP {r.status_code}", file=sys.stderr)
        return 4
    ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
    ext = EXT_BY_TYPE.get(ctype) or Path(urlparse(str(r.url)).path).suffix.lower() or mimetypes.guess_extension(ctype) or ".bin"
    if ext not in {".pdf", ".html", ".htm", ".txt"}:
        print(f"Unsupported content type '{ctype}' ({ext}). Download it manually into kb/raw/{a.layer}/.", file=sys.stderr)
        return 5
    if ext == ".pdf" and not r.content.startswith(b"%PDF"):
        print("The server did not return a real PDF (maybe a login or cookie page). Download it in a browser instead.",
              file=sys.stderr)
        return 6

    dest = kb / "raw" / a.layer / f"{doc_id}{ext}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    append_row(kb, {
        "doc_id": doc_id, "title": a.title, "issuing_body": a.issuing_body, "law_number": a.law_number,
        "year": a.year, "status": a.status, "layer": a.layer, "language": a.language,
        "translation_of": a.translation_of, "domains": a.domains, "url": a.url,
        "retrieved_at": date.today().isoformat(), "verified": "false",
        "local_file": dest.relative_to(kb).as_posix(), "notes": "added by add_source",
    })
    print(f"Saved {dest.relative_to(kb.parent)} ({len(r.content) // 1024} KB) and registered '{doc_id}'.")
    print("Next: check the row in kb/sources.csv (set verified=true once checked), then run python -m app.kb.ingest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
