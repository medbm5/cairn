from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from cairn.config import get_settings
from cairn.explain.client import OpenAIExplainer
from cairn.explain.service import Explanation, RateLimiter, ResponseCache, explain
from cairn.schemas import ExplainRequest

router = APIRouter(tags=["explain"])

response_cache = ResponseCache()
rate_limiter = RateLimiter(limit=60, window=60.0)


@lru_cache
def get_explainer() -> OpenAIExplainer | None:
    """The OpenAI explainer, or None when no key is configured (templates are used instead)."""
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    return OpenAIExplainer(settings.openai_api_key, settings.openai_model)


def get_cache() -> ResponseCache:
    return response_cache


def get_rate_limiter() -> RateLimiter:
    return rate_limiter


@router.post("/explain")
def post_explain(
    body: ExplainRequest,
    request: Request,
    explainer: Annotated[OpenAIExplainer | None, Depends(get_explainer)],
    cache: Annotated[ResponseCache, Depends(get_cache)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> Explanation:
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.allow(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many explanations in a short time. Wait a minute and try again.",
            headers={"Retry-After": str(int(limiter.window))},
        )
    return explain(
        topic=body.topic,
        facts=body.parsed_facts(),
        term=body.term,
        level=body.level,
        language=body.language,
        explainer=explainer,
        cache=cache,
    )
