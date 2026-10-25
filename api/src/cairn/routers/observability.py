"""Observability for the demo: API traffic, LLM usage and the log trail since the last start.

Demo-scoped and without authentication like the rest of the API (ADR 0004): it exposes request
paths, timings and token counts, never request bodies, questions or keys.
"""

from typing import Annotated

from fastapi import APIRouter, Query

from cairn import observability
from cairn.config import get_settings
from cairn.schemas import ObservabilityStats

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/stats")
def get_stats(recent: Annotated[int, Query(ge=1, le=200)] = 50) -> ObservabilityStats:
    settings = get_settings()
    return ObservabilityStats.model_validate(
        observability.stats(
            model=settings.openai_model, ai_enabled=bool(settings.openai_api_key), recent=recent
        )
    )
