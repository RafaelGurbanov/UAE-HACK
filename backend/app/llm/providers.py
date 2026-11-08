"""Concrete providers: Anthropic (default), OpenAI-compatible (Ollama / vLLM /
ITU sandbox), and a deterministic mock for tests and offline demos."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

import httpx

from app.core.config import Settings
from app.llm.base import LLMResult


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, settings: Settings):
        from anthropic import AsyncAnthropic  # imported lazily: optional dependency path

        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to the .env file in the project root, "
                               "then restart the backend.")
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=settings.llm_timeout_s)
        self._model = settings.llm_model

    def _system(self, system: str | None, cache: bool):
        if not system:
            return None
        if cache:  # prompt caching for long, stable system prompts (agent mandates, answer format)
            return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        return system

    async def complete(self, messages, *, system=None, model=None, max_tokens=1024,
                       temperature=0.0, json_mode=False, cache_system=False) -> LLMResult:
        t0 = time.perf_counter()
        kwargs = {}
        sys_block = self._system(system, cache_system)
        if sys_block:
            kwargs["system"] = sys_block
        resp = await self._client.messages.create(
            model=model or self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            **kwargs,
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        return LLMResult(
            text=text, model=resp.model, provider=self.name,
            input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens,
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )

    async def stream(self, messages, *, system=None, model=None, max_tokens=1024,
                     temperature=0.0) -> AsyncIterator[str]:
        kwargs = {}
        sys_block = self._system(system, True)  # long, stable system prompts: cache them
        if sys_block:
            kwargs["system"] = sys_block
        async with self._client.messages.stream(
            model=model or self._model, max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": m.role, "content": m.content} for m in messages], **kwargs,
        ) as s:
            async for chunk in s.text_stream:
                yield chunk


class OpenAICompatProvider:
    """Works with Ollama (`http://host:11434/v1`), vLLM, LM Studio, and any
    sandbox exposing /chat/completions."""

    name = "openai_compat"

    def __init__(self, settings: Settings):
        self._base = settings.openai_compat_base_url.rstrip("/")
        self._key = settings.openai_compat_api_key
        self._model = settings.llm_model
        self._timeout = settings.llm_timeout_s

    def _payload(self, messages, system, model, max_tokens, temperature, stream, json_mode=False):
        msgs = ([{"role": "system", "content": system}] if system else []) + [
            {"role": m.role, "content": m.content} for m in messages
        ]
        p = {"model": model or self._model, "messages": msgs, "max_tokens": max_tokens,
             "temperature": temperature, "stream": stream}
        if json_mode:
            p["response_format"] = {"type": "json_object"}
        return p

    async def complete(self, messages, *, system=None, model=None, max_tokens=1024,
                       temperature=0.0, json_mode=False, cache_system=False) -> LLMResult:
        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=self._timeout) as c:
            r = await c.post(f"{self._base}/chat/completions",
                             headers={"Authorization": f"Bearer {self._key}"},
                             json=self._payload(messages, system, model, max_tokens, temperature, False, json_mode))
            r.raise_for_status()
            data = r.json()
        usage = data.get("usage") or {}
        return LLMResult(
            text=data["choices"][0]["message"]["content"] or "", model=data.get("model", model or self._model),
            provider=self.name, input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )

    async def stream(self, messages, *, system=None, model=None, max_tokens=1024,
                     temperature=0.0) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=self._timeout) as c:
            async with c.stream("POST", f"{self._base}/chat/completions",
                                headers={"Authorization": f"Bearer {self._key}"},
                                json=self._payload(messages, system, model, max_tokens, temperature, True)) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line.startswith("data: ") or line.endswith("[DONE]"):
                        continue
                    delta = json.loads(line[6:])["choices"][0].get("delta", {}).get("content")
                    if delta:
                        yield delta


class MockProvider:
    """Deterministic, offline. Echoes a fixed string; JSON mode returns {}."""

    name = "mock"

    def __init__(self, settings: Settings | None = None):
        self._model = "mock-1"

    async def complete(self, messages, *, system=None, model=None, max_tokens=1024,
                       temperature=0.0, json_mode=False, cache_system=False) -> LLMResult:
        text = "{}" if json_mode else f"[mock answer to: {messages[-1].content[:80]}]"
        return LLMResult(text=text, model=self._model, provider=self.name)

    async def stream(self, messages, *, system=None, model=None, max_tokens=1024,
                     temperature=0.0) -> AsyncIterator[str]:
        for word in f"[mock answer to: {messages[-1].content[:80]}]".split(" "):
            yield word + " "
