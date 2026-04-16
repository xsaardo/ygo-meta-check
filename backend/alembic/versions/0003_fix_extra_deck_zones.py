"""Fix deck_cards where extra deck card types were incorrectly stored as zone='main'.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-15
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Use keyword matching — ygoprodeck stores subtypes like "Link Effect Monster",
    # "Synchro Tuner Monster", etc. The keywords fusion/synchro/xyz/link uniquely
    # identify extra deck cards regardless of subtype suffix.
    op.execute(
        """
        UPDATE deck_cards
        SET zone = 'extra'
        WHERE zone = 'main'
          AND (
            card_type ILIKE '%Fusion%Monster%'
            OR card_type ILIKE '%Synchro%Monster%'
            OR card_type ILIKE '%XYZ%Monster%'
            OR card_type ILIKE '%Link%Monster%'
          )
        """
    )


def downgrade() -> None:
    # Cannot reliably reverse — would need to re-run the scraper
    pass
