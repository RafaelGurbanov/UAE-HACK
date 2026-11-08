"""Structured knowledge-base entries: kb/data/*.json (each file = a JSON list of entries).

The Pydantic model below IS the schema; kb/data/schema.json is generated from it
(`python -m app.kb.validate_data --write-schema`) so the two never drift.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from app.core.taxonomy import KBLayer, PipelineNode, ReadinessDimension

log = logging.getLogger(__name__)
PLACEHOLDER = "SOURCE TO BE VERIFIED"


class Keywords(BaseModel):
    model_config = ConfigDict(extra="forbid")
    en: list[str] = Field(default_factory=list, description="English search terms and paraphrases")
    ar: list[str] = Field(default_factory=list, description="Arabic search terms and paraphrases")
    az: list[str] = Field(default_factory=list, description="Azerbaijani search terms and paraphrases")


class DataCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    law: str = Field(..., min_length=1, description=f'Official law/document title, or "{PLACEHOLDER}"')
    article: str = Field(..., min_length=1, description=f'Article / clause, or "{PLACEHOLDER}"')
    layer: KBLayer
    url: str = Field("", description="Official URL; empty until verified")
    quote: str = Field(..., min_length=1, description=f'Exact quote from the official text, or "{PLACEHOLDER}"')
    verified: bool = Field(False, description="true ONLY after a person checked law, article and quote against the official source")


class DataEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., pattern=r"^[a-z0-9][a-z0-9_\-]{2,63}$", description="Unique, stable id (lowercase, digits, _ or -)")
    topic: str = Field(..., min_length=2)
    keywords: Keywords
    question: str = Field(..., min_length=5, description="The canonical question this entry answers")
    answer: str = Field(..., min_length=10)
    citations: list[DataCitation] = Field(default_factory=list)
    pipeline_nodes: list[PipelineNode] = Field(default_factory=list)
    readiness_dimensions: list[ReadinessDimension] = Field(default_factory=list)
    requires_human_decision: bool = False
    status: Literal["draft", "reviewed", "approved", "retired"] = Field(
        "draft", description="Editorial status of this entry. 'retired' entries are never returned.")
    last_checked: date | None = Field(None, description="Date the entry was last checked (YYYY-MM-DD)")


ENTRY_LIST = TypeAdapter(list[DataEntry])


def json_schema() -> dict:
    schema = ENTRY_LIST.json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "Qalam knowledge-base data file (a list of entries)"
    return schema


@dataclass
class DataLoad:
    entries: list[DataEntry] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    file_of: dict[str, str] = field(default_factory=dict)


def data_files(data_dir: Path) -> list[Path]:
    return sorted(p for p in data_dir.glob("*.json") if p.name != "schema.json")


def load_data(data_dir: Path) -> DataLoad:
    """Load and validate every kb/data/*.json. Invalid files are skipped and reported, never fatal."""
    out = DataLoad()
    if not data_dir.exists():
        return out
    for f in data_files(data_dir):
        out.files.append(f.name)
        try:
            raw = json.loads(f.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as e:
            out.errors.append(f"{f.name}: invalid JSON at line {e.lineno} column {e.colno}: {e.msg}")
            continue
        try:
            entries = ENTRY_LIST.validate_python(raw)
        except ValidationError as e:
            for err in e.errors():
                loc = err["loc"]
                where = f"entry {loc[0]}" + (f" (id={raw[loc[0]].get('id')!r})" if isinstance(loc[0], int)
                                             and isinstance(raw, list) and isinstance(raw[loc[0]], dict) else "")
                fieldpath = ".".join(str(x) for x in loc[1:]) or "(entry)"
                out.errors.append(f"{f.name}: {where}, field {fieldpath}: {err['msg']}")
            continue
        for e in entries:
            if e.id in out.file_of:
                out.duplicates.append(f"duplicate id '{e.id}' in {f.name} (already in {out.file_of[e.id]})")
                continue
            out.file_of[e.id] = f.name
            out.entries.append(e)
    for d in out.duplicates:
        out.errors.append(d)
    if out.errors:
        for msg in out.errors:
            log.error("kb/data: %s", msg)
    log.info("kb/data: %d entries from %d files (%d problems)", len(out.entries), len(out.files), len(out.errors))
    return out
