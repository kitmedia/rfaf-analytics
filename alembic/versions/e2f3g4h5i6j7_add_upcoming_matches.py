"""add_upcoming_matches

Revision ID: e2f3g4h5i6j7
Revises: d1e2f3g4h5i6
Create Date: 2026-04-14 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'e2f3g4h5i6j7'
down_revision: Union[str, None] = 'd1e2f3g4h5i6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'upcoming_matches',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('club_id', UUID(as_uuid=True), sa.ForeignKey('clubs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rival_name', sa.String(200), nullable=False),
        sa.Column('match_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('competition', sa.String(200), nullable=True),
        sa.Column('source', sa.String(50), nullable=False, server_default='manual_input'),
        sa.Column('auto_analysis_id', UUID(as_uuid=True), sa.ForeignKey('match_analyses.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notification_sent', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_upcoming_matches_club_id', 'upcoming_matches', ['club_id'])
    op.create_index('ix_upcoming_matches_match_date', 'upcoming_matches', ['match_date'])


def downgrade() -> None:
    op.drop_table('upcoming_matches')
