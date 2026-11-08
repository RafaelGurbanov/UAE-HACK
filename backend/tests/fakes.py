"""Test-only fake LLM. Builds a tagged answer by quoting the first retrieved source verbatim,
so the real parser + citation verifier are exercised end to end without network."""

import re

from app.llm.base import LLMResult


class SourceQuotingLLM:
    name = "fake"

    def __init__(self, bad_quote: bool = False):
        self.bad_quote = bad_quote
        self.calls: list[str] = []

    async def complete(self, messages, **kw):
        self.calls.append("complete")
        import json

        q = messages[-1].content.split("Question:", 1)[-1].strip()
        return LLMResult(text=json.dumps({"en": [q], "ar": [], "keywords": []}), model="fake", provider="fake")

    async def stream(self, messages, system=None, **kw):
        self.calls.append("stream")
        prompt = messages[-1].content
        if "SOURCES:" not in prompt:  # general mode
            for w in "General answer, not from the knowledge base.".split():
                yield w + " "
            return
        body = prompt.split("SOURCES:", 1)[1].split("\n", 3)[3]  # skip "\n\nS1 | header\n"
        sentence = re.split(r"(?<=[.])\s", body.strip())[0]
        quote = "This sentence does not exist in any source text." if self.bad_quote else sentence
        out = (f"<short_answer>The source sets the rule for this question [c1].</short_answer>\n"
               f"<details></details>\n<status_and_limits>Test status.</status_and_limits>\n<related></related>\n"
               f"<citations>\n[c1] S1 | {quote}\n</citations>\n"
               f"<tags>nodes: SRC, P, BOGUS\ndimensions: human_interaction_supervision\nchild_affected: yes</tags>")
        for i in range(0, len(out), 17):
            yield out[i : i + 17]
