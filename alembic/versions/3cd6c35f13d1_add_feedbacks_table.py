"""add_feedbacks_table

Revision ID: 3cd6c35f13d1
Revises: 03f0677b30e7
Create Date: 2026-04-10 14:15:12.565204

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '3cd6c35f13d1'
down_revision: Union[str, None] = '03f0677b30e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    feedback_category = sa.Enum(
        'usabilidad', 'precision', 'velocidad', 'funcionalidad', 'otro',
        name='feedback_category',
    )
    feedback_category.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'feedbacks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('club_id', UUID(as_uuid=True), sa.ForeignKey('clubs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('analysis_id', UUID(as_uuid=True), sa.ForeignKey('match_analyses.id', ondelete='SET NULL'), nullable=True),
        sa.Column('category', sa.Enum('usabilidad', 'precision', 'velocidad', 'funcionalidad', 'otro', name='feedback_category', create_type=False), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='ck_feedback_rating_range'),
    )
    op.create_index('ix_feedbacks_club_id', 'feedbacks', ['club_id'])


def downgrade() -> None:
    op.drop_table('feedbacks')
    sa.Enum(name='feedback_category').drop(op.get_bind(), checkfirst=True)
