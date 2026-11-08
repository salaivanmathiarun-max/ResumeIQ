import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.resume import Resume


class AnalysisStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class ResumeAnalysis(Base):
    __tablename__ = "resume_analyses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Status & Operational metadata
    analysis_status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus),
        nullable=False,
        default=AnalysisStatus.pending,
    )
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    analysis_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Resume Compatibility Scores (0-100)
    compatibility_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    section_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impact_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    formatting_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Summary & Evidence-based Analysis Data (JSON structured)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    identified_sections: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    skills_categorized: Mapped[Dict[str, List[str]]] = mapped_column(JSON, nullable=False, default=dict)
    strengths: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    improvements: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    suggested_roles: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    missing_or_uncertain_elements: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    scoring_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    # Relationship back to Resume
    resume: Mapped["Resume"] = relationship(
        "Resume",
        back_populates="analysis",
    )
