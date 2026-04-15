"""add_federation_conventions

Revision ID: f3g4h5i6j7k8
Revises: e2f3g4h5i6j7
Create Date: 2026-04-15 01:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = 'f3g4h5i6j7k8'
down_revision: Union[str, None] = 'e2f3g4h5i6j7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'federation_conventions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('federation_name', sa.String(200), nullable=False),
        sa.Column('discount_code', sa.String(50), unique=True, nullable=False),
        sa.Column('discount_pct', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_federation_conventions_code', 'federation_conventions', ['discount_code'])

    # Add acquisition_channel to clubs for Story 5.5
    op.add_column('clubs', sa.Column('acquisition_channel', sa.String(50), nullable=True, server_default='direct'))
    op.add_column('clubs', sa.Column('federation_convention_id', UUID(as_uuid=True), nullable=True))

def downgrade() -> None:
    op.drop_column('clubs', 'federation_convention_id')
    op.drop_column('clubs', 'acquisition_channel')
    op.drop_table('federation_conventions')
