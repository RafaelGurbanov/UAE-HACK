"""Check kb/data/*.json and print a summary.

    python -m app.kb.validate_data                 # check everything
    python -m app.kb.validate_data --write-schema  # regenerate kb/data/schema.json from the model

Exit code 1 on schema errors or duplicate ids; warnings (missing citations,
verified=false, drafts, stale last_checked) do not fail.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from app.core.config import get_settings
from app.kb.data_model import PLACEHOLDER, json_schema, load_data

STALE_DAYS = 180


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write-schema", action="store_true")
    a = ap.parse_args(argv)
    d = get_settings().data_dir
    if a.write_schema:
        d.mkdir(parents=True, exist_ok=True)
        (d / "schema.json").write_text(json.dumps(json_schema(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {d / 'schema.json'}")

    r = load_data(d)
    no_cit = [e.id for e in r.entries if not e.citations]
    unverified = [e.id for e in r.entries if any(not c.verified for c in e.citations)]
    placeholders = [e.id for e in r.entries if any(PLACEHOLDER in (c.law + c.article + c.quote) for c in e.citations)]
    drafts = [e.id for e in r.entries if e.status == "draft"]
    retired = [e.id for e in r.entries if e.status == "retired"]
    stale = [e.id for e in r.entries if e.last_checked is None or (date.today() - e.last_checked).days > STALE_DAYS]
    n_cit = sum(len(e.citations) for e in r.entries)
    n_ver = sum(c.verified for e in r.entries for c in e.citations)

    print(f"\nkb/data summary ({d})")
    print(f"  files:                  {len(r.files)}  ({', '.join(r.files) or '-'})")
    print(f"  valid entries:          {len(r.entries)}")
    print(f"  citations:              {n_cit} ({n_ver} verified, {n_cit - n_ver} to be verified)")
    print(f"  schema errors:          {len([x for x in r.errors if not x.startswith('duplicate id')])}")
    print(f"  duplicate ids:          {len(r.duplicates)}")

    def show(label: str, ids: list[str]):
        print(f"  {label:24}{len(ids)}" + (f"  -> {', '.join(ids)}" if ids else ""))

    show("missing citations:", no_cit)
    show("verified=false:", unverified)
    show("placeholder sources:", placeholders)
    show("status draft:", drafts)
    show("status retired:", retired)
    show(f"not checked in {STALE_DAYS}d:", stale)
    if r.errors:
        print("\nErrors:")
        for e in r.errors:
            print(f"  - {e}")
    print("\nResult:", "FAILED" if r.errors else "OK" + (" (with warnings)" if no_cit or unverified or stale else ""))
    return 1 if r.errors else 0


if __name__ == "__main__":
    sys.exit(main())
