"""Thin wrapper around the official OpenAI SDK, returning structured output or None.

Kept cheap on purpose: the smallest model, minimal reasoning, a short system prompt and a tight
output cap. Every call is recorded (tokens, latency, estimated cost) for the observability page.
"""

import time

import openai
from pydantic import BaseModel, Field

from cairn.logging import get_logger
from cairn.observability import record_llm_call

log = get_logger("cairn.explain")

SYSTEM_PROMPT = """\
You are Pebble, a friendly guide in an investing demo, explaining finance to first-time savers \
in everyday words.
Rules: use only numbers from FACTS, never calculate or add your own. Explain, never advise or \
promise returns. Explain any finance word or use a GLOSSARY term. Warm, concrete, brief, active \
voice, no exclamation marks or emoji. Write amounts as people do (€1,183.07 in English, \
1 183,07 € in French; a fall rather than a minus sign) and never show field names. Write in \
LANGUAGE within the word limit. analogy: one short everyday comparison or null. terms_used: \
the GLOSSARY keys you relied on."""

# Reasoning models accept an effort setting; minimal keeps hidden reasoning tokens near zero.
REASONING_PREFIXES = ("gpt-5", "o1", "o3", "o4")


class GeneratedExplanation(BaseModel):
    title: str = Field(description="A heading of two to six words, in LANGUAGE.")
    body: str
    analogy: str | None
    terms_used: list[str]


class OpenAIExplainer:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout: float = 10.0,
        max_retries: int = 1,
        max_output_tokens: int = 400,
    ) -> None:
        self._client = openai.OpenAI(api_key=api_key, timeout=timeout, max_retries=max_retries)
        self.model = model
        self._max_output_tokens = max_output_tokens

    def generate(self, prompt: str, *, topic: str = "") -> GeneratedExplanation | None:
        """Ask the model for an explanation. Returns None on any API error or empty output."""
        reasoning = self.model.startswith(REASONING_PREFIXES)
        extra = {"reasoning": {"effort": "minimal"}} if reasoning else {}
        started = time.perf_counter()
        try:
            response = self._client.responses.parse(
                model=self.model,
                instructions=SYSTEM_PROMPT,
                input=prompt,
                text_format=GeneratedExplanation,
                max_output_tokens=self._max_output_tokens,
                **extra,  # type: ignore[arg-type]
            )
        except openai.OpenAIError as exc:
            log.warning("explain.openai_error", error=type(exc).__name__)
            record_llm_call(
                topic=topic,
                model=self.model,
                ok=False,
                latency_ms=(time.perf_counter() - started) * 1000,
                error=type(exc).__name__,
            )
            return None
        usage = response.usage
        details = getattr(usage, "output_tokens_details", None)
        record_llm_call(
            topic=topic,
            model=self.model,
            ok=response.output_parsed is not None,
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
            reasoning_tokens=getattr(details, "reasoning_tokens", 0) or 0,
            latency_ms=(time.perf_counter() - started) * 1000,
            error=None if response.output_parsed is not None else "empty_output",
        )
        return response.output_parsed
