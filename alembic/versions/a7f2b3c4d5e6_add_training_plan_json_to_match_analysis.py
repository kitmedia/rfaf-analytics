"""add_training_plan_json_to_match_analysis

Revision ID: a7f2b3c4d5e6
Revises: 3cd6c35f13d1
Create Date: 2026-04-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'a7f2b3c4d5e6'
down_revision: Union[str, None] = '3cd6c35f13d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('match_analyses', sa.Column('training_plan_json', JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('match_analyses', 'training_plan_json')
