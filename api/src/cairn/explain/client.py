"""Thin wrapper around the official OpenAI SDK, returning structured output or None."""

import openai
from pydantic import BaseModel

from cairn.logging import get_logger

log = get_logger("cairn.explain")

SYSTEM_PROMPT = """\
You are Pebble, a friendly guide in a goal-based investing demo. You explain finance to people \
who have never invested, in everyday words.

Rules:
- Use only the numbers given in FACTS. Never calculate, estimate, round to a new figure, or add \
numbers of your own. If a number is not in FACTS, do not write it.
- Explain; never advise. Do not tell the person what to do, buy or sell.
- Never promise or predict returns. Projections are estimates, not promises.
- Every finance word you use must be explained in plain words, or be one of the GLOSSARY terms.
- Be concrete, warm and brief. Active voice. No exclamation marks, no emoji.
- Write in the requested LANGUAGE.
- `body` must stay within the requested word limit.
- `analogy` is one short everyday comparison, or null.
- `terms_used` lists the GLOSSARY keys of the terms your text relies on.
"""


class GeneratedExplanation(BaseModel):
    title: str
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
        max_output_tokens: int = 800,
    ) -> None:
        self._client = openai.OpenAI(api_key=api_key, timeout=timeout, max_retries=max_retries)
        self._model = model
        self._max_output_tokens = max_output_tokens

    def generate(self, prompt: str) -> GeneratedExplanation | None:
        """Ask the model for an explanation. Returns None on any API error or empty output."""
        try:
            response = self._client.responses.parse(
                model=self._model,
                instructions=SYSTEM_PROMPT,
                input=prompt,
                text_format=GeneratedExplanation,
                max_output_tokens=self._max_output_tokens,
            )
        except openai.OpenAIError as exc:
            log.warning("explain.openai_error", error=type(exc).__name__)
            return None
        return response.output_parsed
