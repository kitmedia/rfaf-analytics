"""initial_schema_7_tables

Revision ID: aeaab1d695e3
Revises:
Create Date: 2026-04-10 11:16:32.175033

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision: str = 'aeaab1d695e3'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enums
    plan_type = sa.Enum('basico', 'profesional', 'federado', name='plan_type')
    plan_type.create(op.get_bind(), checkfirst=True)

    user_role = sa.Enum('entrenador', 'admin', 'manager', name='user_role')
    user_role.create(op.get_bind(), checkfirst=True)

    analysis_status = sa.Enum('pending', 'processing', 'done', 'error', name='analysis_status')
    analysis_status.create(op.get_bind(), checkfirst=True)

    player_position = sa.Enum('GK', 'DEF', 'MID', 'FWD', name='player_position')
    player_position.create(op.get_bind(), checkfirst=True)

    scout_type = sa.Enum('player_scout', 'rival_analysis', name='scout_type')
    scout_type.create(op.get_bind(), checkfirst=True)

    physical_status = sa.Enum('healthy', 'fatigue', 'risk', 'injured', name='physical_status')
    physical_status.create(op.get_bind(), checkfirst=True)

    # clubs
    op.create_table(
        'clubs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('plan', sa.Enum('basico', 'profesional', 'federado', name='plan_type', create_type=False), nullable=False, server_default='basico'),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('analisis_mes_actual', sa.Integer(), default=0, server_default='0'),
        sa.Column('active', sa.Boolean(), default=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint('analisis_mes_actual >= 0', name='ck_club_analisis_positivo'),
    )

    # users
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('club_id', UUID(as_uuid=True), sa.ForeignKey('clubs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('role', sa.Enum('entrenador', 'admin', 'manager', name='user_role', create_type=False), nullable=False, server_default='entrenador'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_users_club_id', 'users', ['club_id'])

    # matches
    op.create_table(
        'matches',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('club_id', UUID(as_uuid=True), sa.ForeignKey('clubs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('youtube_url', sa.String(500), nullable=False),
        sa.Column('equipo_local', sa.String(200), nullable=False),
        sa.Column('equipo_visitante', sa.String(200), nullable=False),
        sa.Column('competicion', sa.String(200), nullable=True),
        sa.Column('tactical_data', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_matches_club_id', 'matches', ['club_id'])
    op.create_index('ix_matches_youtube_url', 'matches', ['youtube_url'])

    # match_analyses
    op.create_table(
        'match_analyses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('match_id', UUID(as_uuid=True), sa.ForeignKey('matches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('club_id', UUID(as_uuid=True), sa.ForeignKey('clubs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'processing', 'done', 'error', name='analysis_status', create_type=False), nullable=False, server_default='pending'),
        sa.Column('progress_pct', sa.Integer(), default=0, server_default='0'),
        sa.Column('current_step', sa.String(200), nullable=True),
        sa.Column('estimated_remaining_seconds', sa.Integer(), nullable=True),
        sa.Column('xg_local', sa.Float(), nullable=True),
        sa.Column('xg_visitante', sa.Float(), nullable=True),
        sa.Column('contenido_md', sa.Text(), nullable=True),
        sa.Column('pdf_url', sa.String(500), nullable=True),
        sa.Column('charts_json', JSON, nullable=True),
        sa.Column('cost_gemini', sa.Float(), nullable=True),
        sa.Column('cost_claude', sa.Float(), nullable=True),
        sa.Column('duration_s', sa.Float(), nullable=True),
        sa.Column('model_gemini', sa.String(100), server_default='gemini-2.5-flash'),
        sa.Column('model_claude', sa.String(100), server_default='claude-sonnet-4-6'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint('progress_pct >= 0 AND progress_pct <= 100', name='ck_analysis_progress_range'),
    )
    op.create_index('ix_match_analyses_club_id', 'match_analyses', ['club_id'])
    op.create_index('ix_match_analyses_status', 'match_analyses', ['status'])

    # players
    op.create_table(
        'players',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('club_id', UUID(as_uuid=True), sa.ForeignKey('clubs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('match_id', UUID(as_uuid=True), sa.ForeignKey('matches.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('shirt_number', sa.Integer(), nullable=True),
        sa.Column('position', sa.Enum('GK', 'DEF', 'MID', 'FWD', name='player_position', create_type=False), nullable=True),
        sa.Column('heatmap_data', JSON, nullable=True),
        sa.Column('stats', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_players_club_id', 'players', ['club_id'])

    # scout_reports
    op.create_table(
        'scout_reports',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('club_id', UUID(as_uuid=True), sa.ForeignKey('clubs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('player_id', UUID(as_uuid=True), sa.ForeignKey('players.id', ondelete='SET NULL'), nullable=True),
        sa.Column('analysis_id', UUID(as_uuid=True), sa.ForeignKey('match_analyses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scout_type', sa.Enum('player_scout', 'rival_analysis', name='scout_type', create_type=False), nullable=False),
        sa.Column('status', sa.Enum('pending', 'processing', 'done', 'error', name='analysis_status', create_type=False), nullable=False, server_default='pending'),
        sa.Column('contenido_md', sa.Text(), nullable=True),
        sa.Column('pdf_url', sa.String(500), nullable=True),
        sa.Column('model', sa.String(100), server_default='claude-sonnet-4-6'),
        sa.Column('cost_eur', sa.Float(), nullable=True),
        sa.Column('duration_s', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_scout_reports_club_id', 'scout_reports', ['club_id'])

    # player_physicals
    op.create_table(
        'player_physicals',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('club_id', UUID(as_uuid=True), sa.ForeignKey('clubs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('player_id', UUID(as_uuid=True), sa.ForeignKey('players.id', ondelete='CASCADE'), nullable=False),
        sa.Column('match_id', UUID(as_uuid=True), sa.ForeignKey('matches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('distance_m', sa.Float(), nullable=True),
        sa.Column('speed_max_kmh', sa.Float(), nullable=True),
        sa.Column('accel_events', sa.Integer(), nullable=True),
        sa.Column('acwr_score', sa.Float(), nullable=True),
        sa.Column('injury_risk_0_100', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('healthy', 'fatigue', 'risk', 'injured', name='physical_status', create_type=False), nullable=False, server_default='healthy'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint('injury_risk_0_100 IS NULL OR (injury_risk_0_100 >= 0 AND injury_risk_0_100 <= 100)', name='ck_physical_injury_risk_range'),
    )
    op.create_index('ix_player_physicals_club_id', 'player_physicals', ['club_id'])
    op.create_index('ix_player_physicals_player_id', 'player_physicals', ['player_id'])


def downgrade() -> None:
    op.drop_table('player_physicals')
    op.drop_table('scout_reports')
    op.drop_table('players')
    op.drop_table('match_analyses')
    op.drop_table('matches')
    op.drop_table('users')
    op.drop_table('clubs')

    for enum_name in ['physical_status', 'scout_type', 'player_position', 'analysis_status', 'user_role', 'plan_type']:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
