from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.candidate import Candidate
from app.schemas.candidate import CandidateCreate, CandidateRead

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
def create_candidate(payload: CandidateCreate, db: Session = Depends(get_db)):
    # Check email uniqueness
    stmt = select(Candidate).where(Candidate.email == payload.email)
    existing = db.execute(stmt).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A candidate with this email already exists",
        )
    candidate = Candidate(**payload.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get("/", response_model=List[CandidateRead])
def list_candidates(db: Session = Depends(get_db)):
    """List all candidate profiles."""
    stmt = select(Candidate).order_by(Candidate.created_at.desc())
    candidates = db.execute(stmt).scalars().all()
    return candidates


@router.get("/{candidate_id}", response_model=CandidateRead)
def get_candidate(
    candidate_id: int = Path(..., gt=0, description="Candidate ID"),
    db: Session = Depends(get_db),
):
    stmt = select(Candidate).where(Candidate.id == candidate_id)
    candidate = db.execute(stmt).scalar_one_or_none()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate with id {candidate_id} not found",
        )
    return candidate
