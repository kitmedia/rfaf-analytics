"""SQLAlchemy 2.0 Models: Club, User, Match, MatchAnalysis, Player, ScoutReport, PlayerPhysical"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


# --- Enums ---


class PlanType(str, enum.Enum):
    BASICO = "basico"
    PROFESIONAL = "profesional"
    FEDERADO = "federado"


class UserRole(str, enum.Enum):
    ENTRENADOR = "entrenador"
    ADMIN = "admin"
    MANAGER = "manager"


class AnalysisStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class PlayerPosition(str, enum.Enum):
    GK = "GK"
    DEF = "DEF"
    MID = "MID"
    FWD = "FWD"


class ScoutType(str, enum.Enum):
    PLAYER_SCOUT = "player_scout"
    RIVAL_ANALYSIS = "rival_analysis"


class PhysicalStatus(str, enum.Enum):
    HEALTHY = "healthy"
    FATIGUE = "fatigue"
    RISK = "risk"
    INJURED = "injured"


# --- Models ---


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    plan: Mapped[PlanType] = mapped_column(
        Enum(PlanType, name="plan_type"), nullable=False, default=PlanType.BASICO
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    analisis_mes_actual: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sponsor_logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    acquisition_channel: Mapped[str | None] = mapped_column(String(50), default="direct")
    federation_convention_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="club", cascade="all, delete-orphan")
    matches: Mapped[list["Match"]] = relationship(back_populates="club", cascade="all, delete-orphan")
    players: Mapped[list["Player"]] = relationship(back_populates="club", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("analisis_mes_actual >= 0", name="ck_club_analisis_positivo"),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    club_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, default=UserRole.ENTRENADOR
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    club: Mapped["Club"] = relationship(back_populates="users")

    __table_args__ = (
        Index("ix_users_club_id", "club_id"),
    )


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    club_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False
    )
    youtube_url: Mapped[str] = mapped_column(String(500), nullable=False)
    equipo_local: Mapped[str] = mapped_column(String(200), nullable=False)
    equipo_visitante: Mapped[str] = mapped_column(String(200), nullable=False)
    competicion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tactical_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    club: Mapped["Club"] = relationship(back_populates="matches")
    analyses: Mapped[list["MatchAnalysis"]] = relationship(back_populates="match", cascade="all, delete-orphan")
    players: Mapped[list["Player"]] = relationship(back_populates="match")

    __table_args__ = (
        Index("ix_matches_club_id", "club_id"),
        Index("ix_matches_youtube_url", "youtube_url"),
    )


class MatchAnalysis(Base):
    __tablename__ = "match_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    club_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysis_status"),
        nullable=False,
        default=AnalysisStatus.PENDING,
    )
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estimated_remaining_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Metrics
    xg_local: Mapped[float | None] = mapped_column(Float, nullable=True)
    xg_visitante: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Content
    contenido_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    charts_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Training plan (P3)
    training_plan_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Pipeline resilience (NFR-8)
    sections_available: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Cost tracking
    cost_gemini: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_claude: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Model versions
    model_gemini: Mapped[str] = mapped_column(String(100), default="gemini-2.5-flash")
    model_claude: Mapped[str] = mapped_column(String(100), default="claude-sonnet-4-6")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    match: Mapped["Match"] = relationship(back_populates="analyses")
    club: Mapped["Club"] = relationship()
    scout_reports: Mapped[list["ScoutReport"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_match_analyses_club_id", "club_id"),
        Index("ix_match_analyses_status", "status"),
        CheckConstraint("progress_pct >= 0 AND progress_pct <= 100", name="ck_analysis_progress_range"),
    )


class Player(Base):
    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    club_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False
    )
    match_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    shirt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position: Mapped[PlayerPosition | None] = mapped_column(
        Enum(PlayerPosition, name="player_position"), nullable=True
    )
    heatmap_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    club: Mapped["Club"] = relationship(back_populates="players")
    match: Mapped["Match | None"] = relationship(back_populates="players")
    physicals: Mapped[list["PlayerPhysical"]] = relationship(back_populates="player", cascade="all, delete-orphan")
    scout_reports: Mapped[list["ScoutReport"]] = relationship(back_populates="player")

    __table_args__ = (
        Index("ix_players_club_id", "club_id"),
    )


class ScoutReport(Base):
    __tablename__ = "scout_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    club_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False
    )
    player_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="SET NULL"), nullable=True
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("match_analyses.id", ondelete="CASCADE"), nullable=False
    )
    scout_type: Mapped[ScoutType] = mapped_column(
        Enum(ScoutType, name="scout_type"), nullable=False
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysis_status"),
        nullable=False,
        default=AnalysisStatus.PENDING,
    )
    contenido_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    model: Mapped[str] = mapped_column(String(100), default="claude-sonnet-4-6")
    cost_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    club: Mapped["Club"] = relationship()
    player: Mapped["Player | None"] = relationship(back_populates="scout_reports")
    analysis: Mapped["MatchAnalysis"] = relationship(back_populates="scout_reports")

    __table_args__ = (
        Index("ix_scout_reports_club_id", "club_id"),
    )


class PlayerPhysical(Base):
    __tablename__ = "player_physicals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    club_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_max_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    accel_events: Mapped[int | None] = mapped_column(Integer, nullable=True)
    acwr_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    injury_risk_0_100: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[PhysicalStatus] = mapped_column(
        Enum(PhysicalStatus, name="physical_status"),
        nullable=False,
        default=PhysicalStatus.HEALTHY,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    club: Mapped["Club"] = relationship()
    player: Mapped["Player"] = relationship(back_populates="physicals")
    match: Mapped["Match"] = relationship()

    __table_args__ = (
        Index("ix_player_physicals_club_id", "club_id"),
        Index("ix_player_physicals_player_id", "player_id"),
        CheckConstraint(
            "injury_risk_0_100 IS NULL OR (injury_risk_0_100 >= 0 AND injury_risk_0_100 <= 100)",
            name="ck_physical_injury_risk_range",
        ),
    )


class FeedbackCategory(str, enum.Enum):
    USABILIDAD = "usabilidad"
    PRECISION = "precision"
    VELOCIDAD = "velocidad"
    FUNCIONALIDAD = "funcionalidad"
    OTRO = "otro"


class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    club_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False
    )
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("match_analyses.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[FeedbackCategory] = mapped_column(
        Enum(FeedbackCategory, name="feedback_category"), nullable=False
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    club: Mapped["Club"] = relationship()

    __table_args__ = (
        Index("ix_feedbacks_club_id", "club_id"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_feedback_rating_range"),
    )


class ExerciseTracking(Base):
    __tablename__ = "exercise_tracking"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    club_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False
    )
    match_analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("match_analyses.id", ondelete="CASCADE"), nullable=False
    )
    exercise_name: Mapped[str] = mapped_column(String(500), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=True)
    completed_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    club: Mapped["Club"] = relationship()
    analysis: Mapped["MatchAnalysis"] = relationship()

    __table_args__ = (
        Index("ix_exercise_tracking_club_id", "club_id"),
        Index("ix_exercise_tracking_analysis_id", "match_analysis_id"),
        # Unique constraint prevents duplicate exercise tracking
        # UniqueConstraint handled via migration: uq_exercise_tracking_club_analysis_name
    )


class ModelShadowRun(Base):
    __tablename__ = "model_shadow_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("match_analyses.id", ondelete="CASCADE"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    xg_result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    divergence_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    analysis: Mapped["MatchAnalysis"] = relationship()

    __table_args__ = (
        Index("ix_model_shadow_runs_analysis_id", "analysis_id"),
    )


class FederationConvention(Base):
    __tablename__ = "federation_conventions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    federation_name: Mapped[str] = mapped_column(String(200), nullable=False)
    discount_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    discount_pct: Mapped[int] = mapped_column(Integer, default=30)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_federation_conventions_code", "discount_code"),
    )


class UpcomingMatch(Base):
    __tablename__ = "upcoming_matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    club_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False
    )
    rival_name: Mapped[str] = mapped_column(String(200), nullable=False)
    match_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    competition: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual_input")
    auto_analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("match_analyses.id", ondelete="SET NULL"), nullable=True
    )
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    club: Mapped["Club"] = relationship()

    __table_args__ = (
        Index("ix_upcoming_matches_club_id", "club_id"),
        Index("ix_upcoming_matches_match_date", "match_date"),
    )
