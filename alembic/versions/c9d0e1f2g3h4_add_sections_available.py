"""add_sections_available_to_match_analysis

Revision ID: c9d0e1f2g3h4
Revises: b8g3h4i5j6k7
Create Date: 2026-04-14 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = 'c9d0e1f2g3h4'
down_revision: Union[str, None] = 'b8g3h4i5j6k7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('match_analyses', sa.Column('sections_available', JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('match_analyses', 'sections_available')
