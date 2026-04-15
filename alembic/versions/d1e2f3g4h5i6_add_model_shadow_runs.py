"""add_model_shadow_runs

Revision ID: d1e2f3g4h5i6
Revises: c9d0e1f2g3h4
Create Date: 2026-04-14 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = 'd1e2f3g4h5i6'
down_revision: Union[str, None] = 'c9d0e1f2g3h4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'model_shadow_runs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('analysis_id', UUID(as_uuid=True), sa.ForeignKey('match_analyses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('model_version', sa.String(100), nullable=False),
        sa.Column('xg_result_json', JSONB, nullable=True),
        sa.Column('divergence_pct', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_model_shadow_runs_analysis_id', 'model_shadow_runs', ['analysis_id'])


def downgrade() -> None:
    op.drop_table('model_shadow_runs')
