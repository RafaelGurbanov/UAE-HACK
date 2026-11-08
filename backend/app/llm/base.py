"""Provider-neutral LLM interface.

Agents depend only on `LLMProvider`. Swap providers with LLM_PROVIDER in .env.
Retrieval is run by our own code *before* generation (retrieve-then-generate),
so grounding never depends on a provider supporting tool calls. Provider-
specific extras (Claude prompt caching, native tool use) are optional and
must degrade gracefully.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal, Protocol

Role = Literal["user", "assistant"]


@dataclass
class Message:
    role: Role
    content: str


@dataclass
class LLMResult:
    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    extra: dict = field(default_factory=dict)


class LLMProvider(Protocol):
    name: str

    async def complete(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        json_mode: bool = False,
        cache_system: bool = False,
    ) -> LLMResult: ...

    def stream(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> AsyncIterator[str]: ...
