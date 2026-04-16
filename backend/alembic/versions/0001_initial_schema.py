"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tournaments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ygopro_id", sa.Integer(), unique=True, nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=True),
        sa.Column("format", sa.String(50), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("player_count", sa.Integer(), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tournaments_ygopro_id", "tournaments", ["ygopro_id"])
    op.create_index("ix_tournaments_slug", "tournaments", ["slug"])
    op.create_index("ix_tournaments_date", "tournaments", ["date"])

    op.create_table(
        "decks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ygopro_id", sa.Integer(), unique=True, nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False),
        sa.Column("archetype", sa.String(255), nullable=True),
        sa.Column("deck_url", sa.Text(), nullable=False),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_decks_ygopro_id", "decks", ["ygopro_id"])
    op.create_index("ix_decks_slug", "decks", ["slug"])

    op.create_table(
        "placements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tournament_id",
            sa.Integer(),
            sa.ForeignKey("tournaments.id"),
            nullable=False,
        ),
        sa.Column("deck_id", sa.Integer(), sa.ForeignKey("decks.id"), nullable=True),
        sa.Column("placement", sa.String(50), nullable=True),
        sa.Column("player_name", sa.String(255), nullable=True),
    )
    op.create_index("ix_placements_tournament_id", "placements", ["tournament_id"])
    op.create_index("ix_placements_deck_id", "placements", ["deck_id"])

    op.create_table(
        "deck_cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("deck_id", sa.Integer(), sa.ForeignKey("decks.id"), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("card_name", sa.String(255), nullable=False),
        sa.Column("card_type", sa.String(100), nullable=True),
        sa.Column("zone", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, default=1),
    )
    op.create_index("ix_deck_cards_deck_id", "deck_cards", ["deck_id"])
    op.create_index("ix_deck_cards_card_id", "deck_cards", ["card_id"])
    op.create_index("ix_deck_cards_card_name", "deck_cards", ["card_name"])


def downgrade() -> None:
    op.drop_table("deck_cards")
    op.drop_table("placements")
    op.drop_table("decks")
    op.drop_table("tournaments")
