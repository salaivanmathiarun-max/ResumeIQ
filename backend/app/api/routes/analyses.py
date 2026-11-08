import logging
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.analysis import ResumeAnalysis
from app.schemas.analysis import ResumeAnalysisResponse
from app.services.analysis_orchestrator import (
    AnalysisOrchestratorError,
    orchestrate_resume_analysis,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["analysis"])


class AnalyzeRequest(BaseModel):
    api_key: Optional[str] = None
    force_refresh: bool = False

    @field_validator("api_key", mode="before")
    @classmethod
    def clean_api_key(cls, v: Any) -> Optional[str]:
        if isinstance(v, str):
            clean = v.strip()
            return clean if clean else None
        return None


@router.post(
    "/{resume_id}/analyze",
    response_model=ResumeAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze or retry analysis for a resume",
    description="Calculates Resume Compatibility Score and runs AI-powered structured extraction.",
)
def analyze_resume(
    resume_id: int = Path(..., gt=0, description="Resume ID"),
    payload: Optional[AnalyzeRequest] = None,
    db: Session = Depends(get_db),
):
    req_api_key = payload.api_key if payload else None
    force_refresh = payload.force_refresh if payload else False

    try:
        analysis = orchestrate_resume_analysis(
            resume_id=resume_id,
            db=db,
            api_key=req_api_key,
            force_refresh=force_refresh,
        )
        return analysis
    except AnalysisOrchestratorError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected internal error during resume {resume_id} analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal error occurred during resume analysis. Please try again.",
        )


@router.get(
    "/{resume_id}/analysis",
    response_model=ResumeAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve analysis for a resume",
    description="Returns the existing Resume Compatibility Score and analysis data for the given resume.",
)
def get_resume_analysis(
    resume_id: int = Path(..., gt=0, description="Resume ID"),
    db: Session = Depends(get_db),
):
    analysis = db.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == resume_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analysis found for resume with id {resume_id}. Trigger analysis via POST /api/resumes/{resume_id}/analyze.",
        )
    return analysis
