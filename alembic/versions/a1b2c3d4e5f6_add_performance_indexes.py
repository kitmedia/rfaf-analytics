"""add_performance_indexes

Revision ID: a1b2c3d4e5f6
Revises: 3cd6c35f13d1
Create Date: 2026-04-12 10:00:00.000000

Indexes added:
- match_analyses.created_at  — ORDER BY in list queries
- match_analyses.(club_id, created_at)  — composite for filtered + sorted queries
- matches.created_at  — ORDER BY in match queries
- feedbacks.created_at  — ORDER BY in feedback list
- users.email  — login lookup (already has UNIQUE but no explicit btree index)
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '3cd6c35f13d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # match_analyses: sorted list queries
    op.create_index('ix_match_analyses_created_at', 'match_analyses', ['created_at'])
    # composite: most common query is WHERE club_id = ? ORDER BY created_at DESC
    op.create_index(
        'ix_match_analyses_club_id_created_at',
        'match_analyses',
        ['club_id', 'created_at'],
    )

    # matches: ORDER BY created_at in admin/analytics queries
    op.create_index('ix_matches_created_at', 'matches', ['created_at'])

    # feedbacks: ORDER BY created_at DESC
    op.create_index('ix_feedbacks_created_at', 'feedbacks', ['created_at'])

def downgrade() -> None:
    op.drop_index('ix_feedbacks_created_at', table_name='feedbacks')
    op.drop_index('ix_matches_created_at', table_name='matches')
    op.drop_index('ix_match_analyses_club_id_created_at', table_name='match_analyses')
    op.drop_index('ix_match_analyses_created_at', table_name='match_analyses')
