from typing import Annotated

from fastapi import APIRouter, Query

from cairn.domain.glide_path import yearly_allocations
from cairn.domain.profiles import RiskProfile, equity_share
from cairn.schemas import GlidePathPoint, GlidePathResponse

router = APIRouter(tags=["glide path"])


@router.get("/glide-path")
def get_glide_path(
    profile: RiskProfile, horizon_months: Annotated[int, Query(ge=12, le=480)]
) -> GlidePathResponse:
    points = [
        GlidePathPoint(
            year=year,
            months_remaining=remaining,
            weights={asset: round(w, 4) for asset, w in weights.items()},
            equity_share=round(equity_share(weights), 4),
        )
        for year, remaining, weights in yearly_allocations(profile, horizon_months)
    ]
    return GlidePathResponse(profile=profile, horizon_months=horizon_months, points=points)
