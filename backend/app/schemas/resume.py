from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class UploadStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class ResumeBase(BaseModel):
    candidate_id: int = Field(..., gt=0, description="Associated candidate ID")
    original_filename: str = Field(..., min_length=1, max_length=255, description="Original filename")
    file_path: str = Field(..., min_length=1, max_length=1024, description="Path where file is stored")
    file_type: str = Field(..., min_length=1, max_length=50, description="File type or extension (e.g., pdf, docx)")
    upload_status: UploadStatus = Field(default=UploadStatus.pending, description="Current upload status")


class ResumeCreate(ResumeBase):
    extracted_text: Optional[str] = Field(default=None, description="Extracted plain text content")


class ResumeRead(ResumeBase):
    id: int
    extracted_text: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ResumeTextResponse(BaseModel):
    id: int
    candidate_id: int
    original_filename: str
    file_type: str
    upload_status: UploadStatus
    extracted_text: Optional[str] = None
    normalized_text: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
