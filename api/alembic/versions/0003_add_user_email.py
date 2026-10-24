"""add user email for the support view

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-25 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_users_email", "users", ["email"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_column("users", "email")
