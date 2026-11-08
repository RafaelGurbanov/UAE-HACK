"""Pick the answer pipeline: offline (free, no LLM) or the LLM legal adviser."""

from app.agents import legal_adviser, offline
from app.api.schemas import AskRequest
from app.core.config import get_settings


def run(req: AskRequest):
    return offline.run(req) if get_settings().offline else legal_adviser.run(req)
