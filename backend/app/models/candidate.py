import enum
from datetime import datetime
from typing import TYPE_CHECKING, List
from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.resume import Resume


class CandidateType(str, enum.Enum):
    student = "student"
    fresher = "fresher"
    experienced = "experienced"


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    candidate_type: Mapped[CandidateType] = mapped_column(Enum(CandidateType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # One-to-many relationship with resumes
    resumes: Mapped[List["Resume"]] = relationship(
        "Resume",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )
