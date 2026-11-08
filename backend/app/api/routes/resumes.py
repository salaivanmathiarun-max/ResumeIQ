import logging
from pathlib import Path
from typing import List
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path as PathParam, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import ALLOWED_FILE_EXTENSIONS, UPLOAD_DIR
from app.database.dependencies import get_db
from app.models.candidate import Candidate
from app.models.resume import Resume, UploadStatus
from app.schemas.resume import ResumeCreate, ResumeRead, ResumeTextResponse
from app.services.document_parser import DocumentProcessingError, extract_text, normalize_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/upload", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    candidate_id: int = Form(..., gt=0, description="ID of associated candidate"),
    file: UploadFile = File(..., description="PDF or DOCX resume document"),
    db: Session = Depends(get_db),
):
    """
    Upload a resume file (PDF or DOCX), validate file integrity,
    extract plain text content, store securely, and persist metadata in the database.
    """
    # 1. Verify candidate exists before processing or storing file
    cand_stmt = select(Candidate).where(Candidate.id == candidate_id)
    candidate = db.execute(cand_stmt).scalar_one_or_none()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate with id {candidate_id} not found",
        )

    # 2. Sanitize original filename (strip path traversal sequences and null bytes)
    raw_filename = file.filename or "uploaded_resume"
    sanitized_filename = Path(raw_filename.replace("\x00", "")).name
    if "\\" in sanitized_filename:
        sanitized_filename = sanitized_filename.split("\\")[-1]
    if not sanitized_filename or sanitized_filename in (".", ".."):
        sanitized_filename = "uploaded_resume"

    ext = Path(sanitized_filename).suffix.lower()
    if ext not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Only .pdf and .docx files are permitted.",
        )

    # 3. Read uploaded bytes
    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {exc}",
        )

    # 4. Validate binary content and extract text
    try:
        extracted_text, file_type = extract_text(content, sanitized_filename)
    except DocumentProcessingError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unexpected error while processing document: {exc}",
        )

    # 5. Store file securely using a unique UUID filename
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destination_path = UPLOAD_DIR / unique_filename

    try:
        destination_path.write_bytes(content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store file on disk: {exc}",
        )

    # 6. Create database record
    resume = Resume(
        candidate_id=candidate_id,
        original_filename=sanitized_filename,
        file_path=str(destination_path),
        file_type=file_type,
        upload_status=UploadStatus.completed,
        extracted_text=extracted_text,
    )
    db.add(resume)

    try:
        db.commit()
        db.refresh(resume)
    except Exception as exc:
        db.rollback()
        # Clean up disk file to prevent orphaned storage
        if destination_path.exists():
            destination_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while saving resume: {exc}",
        )

    return resume


@router.post("/", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
def create_resume(payload: ResumeCreate, db: Session = Depends(get_db)):
    """Create a resume record using metadata directly (preserved from Phase 2)."""
    cand_stmt = select(Candidate).where(Candidate.id == payload.candidate_id)
    candidate = db.execute(cand_stmt).scalar_one_or_none()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate with id {payload.candidate_id} not found",
        )
    resume = Resume(**payload.model_dump())
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("/", response_model=List[ResumeRead])
def list_resumes(db: Session = Depends(get_db)):
    """Retrieve all resume records."""
    stmt = select(Resume).order_by(Resume.created_at.desc())
    resumes = db.execute(stmt).scalars().all()
    return resumes


@router.get("/{resume_id}/text", response_model=ResumeTextResponse)
def get_resume_text(
    resume_id: int = PathParam(..., gt=0, description="Resume ID"),
    db: Session = Depends(get_db),
):
    """Retrieve extracted plain text, normalized representation, and core metadata for a specific resume."""
    stmt = select(Resume).where(Resume.id == resume_id)
    resume = db.execute(stmt).scalar_one_or_none()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume with id {resume_id} not found",
        )
    normalized = normalize_text(resume.extracted_text) if resume.extracted_text else None
    return ResumeTextResponse(
        id=resume.id,
        candidate_id=resume.candidate_id,
        original_filename=resume.original_filename,
        file_type=resume.file_type,
        upload_status=resume.upload_status,
        extracted_text=resume.extracted_text,
        normalized_text=normalized,
    )


@router.get("/{resume_id}", response_model=ResumeRead)
def get_resume(
    resume_id: int = PathParam(..., gt=0, description="Resume ID"),
    db: Session = Depends(get_db),
):
    """Retrieve a single resume record by ID."""
    stmt = select(Resume).where(Resume.id == resume_id)
    resume = db.execute(stmt).scalar_one_or_none()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume with id {resume_id} not found",
        )
    return resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    resume_id: int = PathParam(..., gt=0, description="Resume ID"),
    db: Session = Depends(get_db),
):
    """
    Delete a resume record and remove its stored file from disk if present.
    Ensures safe deletion: only files strictly inside UPLOAD_DIR (and not symlinks) are removed.
    Allows database cleanup without deleting files outside the upload directory.
    """
    stmt = select(Resume).where(Resume.id == resume_id)
    resume = db.execute(stmt).scalar_one_or_none()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume with id {resume_id} not found",
        )

    # Safely remove file on disk ONLY if it is inside UPLOAD_DIR and is not a symlink
    if resume.file_path:
        try:
            raw_path = Path(resume.file_path)
            upload_dir_resolved = UPLOAD_DIR.resolve()

            # Prevent unlinking if it's a symlink or points outside UPLOAD_DIR
            if raw_path.is_symlink():
                logger.warning(f"Skipping deletion of symlink: {raw_path}")
            else:
                stored_file = raw_path.resolve()
                if stored_file.is_file() and (stored_file == upload_dir_resolved or upload_dir_resolved in stored_file.parents):
                    stored_file.unlink(missing_ok=True)
                else:
                    logger.warning(
                        f"Skipping deletion of file outside UPLOAD_DIR for resume {resume_id}: {raw_path}"
                    )
        except Exception as exc:
            logger.warning(f"Error during safe file cleanup for resume {resume_id}: {exc}")

    # Always delete database record
    db.delete(resume)
    db.commit()
    return None
