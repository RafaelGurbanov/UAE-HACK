"""Gap board (kb/gaps/*.json) and kb/data entry listing. Local files only, no LLM."""

import json

from fastapi import APIRouter, HTTPException
from pydantic import TypeAdapter, ValidationError

from app.api.schemas import DataEntriesResponse, DataEntrySummary, GapsResponse, PolicyGap
from app.core.config import get_settings
from app.core.taxonomy import Domain, GapType, ReadinessDimension
from app.kb.data_model import load_data

router = APIRouter()
_GAPS = TypeAdapter(list[PolicyGap])
SEVERITY = {"low": 0.35, "medium": 0.65, "high": 1.0}


def load_gaps() -> tuple[list[PolicyGap], list[str]]:
    d = get_settings().gaps_dir
    gaps, errors = [], []
    for f in sorted(d.glob("*.json")) if d.exists() else []:
        try:
            gaps += _GAPS.validate_python(json.loads(f.read_text(encoding="utf-8-sig")))
        except (json.JSONDecodeError, ValidationError) as e:
            errors.append(f"{f.name}: {e}")
    return gaps, errors


def radar(gaps: list[PolicyGap]) -> dict[ReadinessDimension, float]:
    """Gap pressure per Readiness dimension: severity-weighted, scaled so the worst dimension is 1."""
    acc = {d: 0.0 for d in ReadinessDimension}
    for g in gaps:
        for dim in g.readiness_dimensions:
            acc[dim] += SEVERITY[g.severity]
    top = max(acc.values()) or 1.0
    return {d: round(v / top, 3) for d, v in acc.items()}


@router.get("/gaps", response_model=GapsResponse, tags=["gap analysis"])
def list_gaps(gap_type: GapType | None = None, domain: Domain | None = None) -> GapsResponse:
    gaps, errors = load_gaps()
    if errors:
        raise HTTPException(500, detail={"code": "gap_data_invalid", "message": "; ".join(errors)[:1000]})
    radar_all = radar(gaps)  # radar always reflects the whole board, filters only narrow the list
    if gap_type:
        gaps = [g for g in gaps if g.gap_type == gap_type]
    if domain:
        gaps = [g for g in gaps if g.domain == domain]
    return GapsResponse(gaps=gaps, readiness_radar=radar_all)


@router.get("/data/entries", response_model=DataEntriesResponse, tags=["knowledge base"])
def list_entries() -> DataEntriesResponse:
    r = load_data(get_settings().data_dir)
    out = [DataEntrySummary(
        id=e.id, topic=e.topic, question=e.question, status=e.status,
        last_checked=e.last_checked.isoformat() if e.last_checked else None,
        layers=sorted({c.layer for c in e.citations}, key=lambda x: x.value), citations=len(e.citations),
        verified_citations=sum(c.verified for c in e.citations), file=r.file_of.get(e.id, ""),
    ) for e in r.entries]
    return DataEntriesResponse(entries=out, errors=r.errors)


@router.get("/data/entries/{entry_id}", tags=["knowledge base"])
def get_entry(entry_id: str) -> dict:
    r = load_data(get_settings().data_dir)
    for e in r.entries:
        if e.id == entry_id:
            return {**e.model_dump(mode="json"), "file": r.file_of.get(e.id, "")}
    raise HTTPException(404, detail={"code": "not_found", "message": f"Unknown entry '{entry_id}'"})
