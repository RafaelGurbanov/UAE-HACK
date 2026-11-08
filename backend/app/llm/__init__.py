from functools import lru_cache

from app.core.config import Settings, get_settings
from app.llm.base import LLMProvider, LLMResult, Message
from app.llm.providers import AnthropicProvider, MockProvider, OpenAICompatProvider

_PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai_compat": OpenAICompatProvider,
    "mock": MockProvider,
}


def build_provider(settings: Settings) -> LLMProvider:
    name = settings.effective_provider
    if name == "offline":
        raise RuntimeError("Offline mode is active (no ANTHROPIC_API_KEY): the backend does not call any LLM. "
                           "Set ANTHROPIC_API_KEY and LLM_PROVIDER=anthropic in .env for AI-generated answers.")
    try:
        return _PROVIDERS[name](settings)
    except KeyError as e:
        raise ValueError(f"Unknown LLM_PROVIDER '{settings.llm_provider}'") from e


@lru_cache
def get_llm() -> LLMProvider:
    return build_provider(get_settings())


__all__ = ["LLMProvider", "LLMResult", "Message", "build_provider", "get_llm"]
