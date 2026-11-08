from app.core.config import Settings
from app.llm import Message, build_provider


async def test_mock_provider_is_swappable():
    p = build_provider(Settings(llm_provider="mock"))
    res = await p.complete([Message("user", "hello")])
    assert p.name == "mock" and "hello" in res.text


def test_openai_compat_builds_without_network():
    p = build_provider(Settings(llm_provider="openai_compat", llm_model="qwen2.5:14b"))
    assert p.name == "openai_compat"
