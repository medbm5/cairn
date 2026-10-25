"""Explain a topic: cached model output when it passes the checks, a template otherwise."""

import hashlib
import json
import threading
import time
from collections import OrderedDict, deque
from typing import Literal

from pydantic import BaseModel

from cairn.explain.client import GeneratedExplanation, OpenAIExplainer
from cairn.explain.facts import FactsModel, SupportAnswerFacts, Topic
from cairn.explain.fallbacks import Text, fallback
from cairn.explain.glossary import GLOSSARY, Language
from cairn.explain.guard import unknown_numbers
from cairn.logging import get_logger
from cairn.observability import record_explanation

log = get_logger("cairn.explain")

Level = Literal["simple", "more_detail"]
WORD_LIMITS: dict[str, int] = {"simple": 60, "more_detail": 140}


class Explanation(BaseModel):
    title: str
    body: str
    analogy: str | None
    terms_used: list[str]
    source: Literal["ai", "fallback"]


class ResponseCache:
    """Small in-memory LRU cache, so the same explanation is never paid for twice."""

    def __init__(self, max_items: int = 1_000) -> None:
        self._items: OrderedDict[str, Explanation] = OrderedDict()
        self._max_items = max_items
        self._lock = threading.Lock()

    def get(self, key: str) -> Explanation | None:
        with self._lock:
            if key in self._items:
                self._items.move_to_end(key)
                return self._items[key]
            return None

    def put(self, key: str, value: Explanation) -> None:
        with self._lock:
            self._items[key] = value
            self._items.move_to_end(key)
            while len(self._items) > self._max_items:
                self._items.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class RateLimiter:
    """Sliding-window limit of `limit` calls per `window` seconds for each key (client IP)."""

    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window
        self._calls: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            calls = self._calls.setdefault(key, deque())
            while calls and now - calls[0] > self.window:
                calls.popleft()
            if len(calls) >= self.limit:
                return False
            calls.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._calls.clear()


def cache_key(
    topic: Topic, facts: FactsModel | None, term: str | None, level: Level, language: Language
) -> str:
    payload = {
        "topic": topic,
        "facts": facts.model_dump(mode="json") if facts else None,
        "term": term,
        "level": level,
        "language": language,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


# The support answer must show how the balance change splits; the split itself is in FACTS.
SUPPORT_INSTRUCTIONS = (
    "SUPPORT ANSWER: a support agent asks FACTS.question about a client. Answer it about that "
    "client, in the third person. For focus month_change, state how much the balance changed in "
    "that month and split the change into exactly these parts, with their figures as given: "
    "market effect, deposits, fees. Negative amounts are losses. A rebalance moves money between "
    "investments and does not change the balance. For focus last_rebalance, give its date and "
    "the amount moved."
)


def compact_json(value: object) -> str:
    """JSON without spaces or escaped accents: fewer tokens for the same facts."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def prompt_facts(facts: FactsModel | None) -> dict[str, object]:
    """The facts as the model sees them: amounts already in euros, so it never has to convert
    (it once divided cents by 1,000). The guard still checks every figure against the cents."""
    if facts is None:
        return {}
    data = facts.model_dump(mode="json", exclude_none=True)
    if isinstance(facts, SupportAnswerFacts) and facts.focus == "last_rebalance":
        # The month's figures are irrelevant to this question: leaving them out saves tokens and
        # keeps the model from mixing them into the answer.
        data = {k: v for k, v in data.items() if k in ("question", "focus") or "rebalance" in k}

    def euros(cents: object) -> object:
        if isinstance(cents, dict):
            return {key: euros(value) for key, value in cents.items()}
        return cents / 100 if isinstance(cents, int) else cents

    return {
        (f"{name.removesuffix('_cents')}_eur" if name.endswith("_cents") else name): (
            euros(value) if name.endswith("_cents") else value
        )
        for name, value in data.items()
    }


def build_prompt(
    topic: Topic,
    facts: FactsModel | None,
    term: str | None,
    level: Level,
    language: Language,
    terms: list[str],
) -> str:
    glossary = {
        key: {"term": GLOSSARY[key].term[language], "meaning": GLOSSARY[key].definition[language]}
        for key in terms
    }
    lines = [
        f"TOPIC: {topic}" + (f" ({term})" if term else ""),
        f"LANGUAGE: {'French' if language == 'fr' else 'English'}",
        f"WORD LIMIT FOR BODY: {WORD_LIMITS[level]}",
        "AMOUNTS: values ending in _eur are euros; copy them exactly.",
        "FRACTIONS: 0.25 means 25%.",
        f"FACTS: {compact_json(prompt_facts(facts))}",
        f"GLOSSARY: {compact_json(glossary)}",
    ]
    if topic == Topic.SUPPORT_ANSWER:
        lines.append(SUPPORT_INSTRUCTIONS)
    return "\n".join(lines)


def check_generated(
    title: str, body: str, analogy: str | None, facts: FactsModel | None, level: Level
) -> str | None:
    """Return why the generated text is rejected, or None if it passes."""
    if len(body.split()) > WORD_LIMITS[level]:
        return "too_long"
    unknown = unknown_numbers(" ".join([title, body, analogy or ""]), facts)
    if unknown:
        return f"unknown_numbers:{unknown}"
    return None


def usable_title(generated: str, template: str) -> str:
    """Small models sometimes echo the schema name as the heading; use the template's then."""
    cleaned = generated.strip()
    if not cleaned or cleaned == GeneratedExplanation.__name__ or len(cleaned.split()) > 10:
        return template
    return cleaned


def explain(
    *,
    topic: Topic,
    facts: FactsModel | None,
    term: str | None,
    level: Level,
    language: Language,
    explainer: OpenAIExplainer | None,
    cache: ResponseCache,
) -> Explanation:
    key = cache_key(topic, facts, term, level, language)
    cached = cache.get(key)
    if cached is not None:
        record_explanation(topic, "cache")
        return cached

    template: Text = fallback(topic, facts, term, level, language)
    # Glossary terms already have a human-written definition and analogy: no model call needed.
    reason: str | None = "no_key" if explainer is None else None
    if topic == Topic.TERM:
        reason = "glossary"
    if reason is None and explainer is not None:
        prompt = build_prompt(topic, facts, term, level, language, template.terms_used)
        generated = explainer.generate(prompt, topic=topic.value)
        if generated is None:
            reason = "model_error"
            log.warning("explain.fallback", topic=topic, reason="no_output")
        else:
            reason = check_generated(
                generated.title, generated.body, generated.analogy, facts, level
            )
            if reason is None:
                explanation = Explanation(
                    title=usable_title(generated.title, template.title),
                    body=generated.body,
                    analogy=generated.analogy,
                    terms_used=[t for t in generated.terms_used if t in GLOSSARY],
                    source="ai",
                )
                cache.put(key, explanation)
                record_explanation(topic, "ai")
                return explanation
            log.warning("explain.guard_rejected", topic=topic, reason=reason)
            reason = "guard_rejected"

    record_explanation(topic, "fallback", reason)
    # Templates are not cached: they are free, and a later call may reach the model.
    return Explanation(
        title=template.title,
        body=template.body,
        analogy=template.analogy,
        terms_used=template.terms_used,
        source="fallback",
    )
