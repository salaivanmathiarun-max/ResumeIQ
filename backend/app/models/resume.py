import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.analysis import ResumeAnalysis


class UploadStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., pdf, docx
    upload_status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus),
        nullable=False,
        default=UploadStatus.pending,
    )
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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

    # Many-to-one relationship with Candidate
    candidate: Mapped["Candidate"] = relationship(
        "Candidate",
        back_populates="resumes",
    )

    # One-to-one relationship with ResumeAnalysis
    analysis: Mapped[Optional["ResumeAnalysis"]] = relationship(
        "ResumeAnalysis",
        back_populates="resume",
        uselist=False,
        cascade="all, delete-orphan",
    )
