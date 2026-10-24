from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from cairn.config import get_settings
from cairn.db import get_session
from cairn.schemas import Health

router = APIRouter(tags=["health"])


@router.get("/health")
def health(session: Annotated[Session, Depends(get_session)]) -> Health:
    try:
        session.execute(text("SELECT 1"))
        database = "ok"
    except SQLAlchemyError:
        database = "unavailable"
    return Health(
        status="ok" if database == "ok" else "degraded",
        database=database,
        environment=get_settings().environment,
    )
