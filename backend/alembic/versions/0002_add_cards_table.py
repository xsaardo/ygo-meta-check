"""add cards table with pg_trgm

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "cards",
        sa.Column("id", sa.Integer(), primary_key=True),  # YGOPRODECK numeric ID
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("archetype", sa.String(255), nullable=True),
        sa.Column("image_path", sa.String(500), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Standard index for prefix matching
    op.create_index("ix_cards_name", "cards", ["name"])

    # GIN trigram index for fast similarity search
    op.execute("CREATE INDEX ix_cards_name_trgm ON cards USING GIN (name gin_trgm_ops)")


def downgrade() -> None:
    op.drop_index("ix_cards_name_trgm", "cards")
    op.drop_index("ix_cards_name", "cards")
    op.drop_table("cards")
