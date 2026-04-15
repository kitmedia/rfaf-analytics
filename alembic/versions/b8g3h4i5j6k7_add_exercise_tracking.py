"""add_exercise_tracking

Revision ID: b8g3h4i5j6k7
Revises: a7f2b3c4d5e6
Create Date: 2026-04-14 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'b8g3h4i5j6k7'
down_revision: Union[str, None] = 'a7f2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'exercise_tracking',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('club_id', UUID(as_uuid=True), sa.ForeignKey('clubs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('match_analysis_id', UUID(as_uuid=True), sa.ForeignKey('match_analyses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('exercise_name', sa.String(500), nullable=False),
        sa.Column('completed', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('completed_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_exercise_tracking_club_id', 'exercise_tracking', ['club_id'])
    op.create_index('ix_exercise_tracking_analysis_id', 'exercise_tracking', ['match_analysis_id'])
    op.create_unique_constraint(
        'uq_exercise_tracking_club_analysis_name',
        'exercise_tracking',
        ['club_id', 'match_analysis_id', 'exercise_name'],
    )


def downgrade() -> None:
    op.drop_table('exercise_tracking')
