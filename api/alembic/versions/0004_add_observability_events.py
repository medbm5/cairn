"""add observability events

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-25 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "observability_events",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("data", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_observability_events_at", "observability_events", ["at"])
    op.create_index("ix_observability_events_kind_at", "observability_events", ["kind", "at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_observability_events_kind_at", table_name="observability_events")
    op.drop_index("ix_observability_events_at", table_name="observability_events")
    op.drop_table("observability_events")
