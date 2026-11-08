from datetime import datetime
from enum import Enum
import email_validator
from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Disable network DNS deliverability checks so validation is fast and works offline/sandboxed
email_validator.CHECK_DELIVERABILITY = False


class CandidateType(str, Enum):
    student = "student"
    fresher = "fresher"
    experienced = "experienced"


class CandidateBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name of candidate")
    email: EmailStr = Field(..., description="Unique email address")
    candidate_type: CandidateType = Field(..., description="Candidate type: student, fresher, or experienced")


class CandidateCreate(CandidateBase):
    pass


class CandidateRead(CandidateBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
