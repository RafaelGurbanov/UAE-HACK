from functools import lru_cache

from fastapi import HTTPException

from app.audit.logger import AuditLogger
from app.core.config import get_settings


@lru_cache
def get_audit() -> AuditLogger:
    return AuditLogger(get_settings().audit_log_path)


def not_implemented(phase: int, what: str) -> HTTPException:
    return HTTPException(
        status_code=501,
        detail={"code": "not_implemented", "message": f"{what} arrives in Phase {phase}", "details": {"phase": phase}},
    )
