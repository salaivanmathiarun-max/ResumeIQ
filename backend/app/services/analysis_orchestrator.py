"""
Analysis Orchestrator Service.

Coordinates:
1. Text validation and candidate profile retrieval.
2. Candidate-type-aware deterministic scoring engine.
3. Google Gemini structured extraction service (grounded skills, strengths, improvements).
4. Safe retry and persistence into ResumeAnalysis model.
"""

import logging
import os
from typing import Optional
from sqlalchemy.orm import Session


from app.models.analysis import AnalysisStatus, ResumeAnalysis
from app.models.candidate import CandidateType
from app.models.resume import Resume
from app.services.gemini_service import (
    CURRENT_MODEL_NAME,
    CURRENT_PROMPT_VERSION,
    GeminiServiceError,
    mask_sensitive_data,
    run_gemini_analysis,
)
from app.services.scoring_engine import calculate_compatibility_score
from app.services.skill_grounding import ground_and_filter_skills

logger = logging.getLogger(__name__)


class AnalysisOrchestratorError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def orchestrate_resume_analysis(
    resume_id: int,
    db: Session,
    api_key: Optional[str] = None,
    force_refresh: bool = False,
) -> ResumeAnalysis:
    """
    Executes or retries resume analysis for a given resume:
    1. Loads the Resume and Candidate records.
    2. Validates extracted text.
    3. Manages existing ResumeAnalysis record (safe retry / upsert).
    4. Computes deterministic Resume Compatibility Score.
    5. Invokes Gemini API for grounded skill categorization, strengths, and improvements.
    6. Persists structured results to database.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise AnalysisOrchestratorError(f"Resume with id {resume_id} not found.", status_code=404)

    raw_text = resume.extracted_text
    if not raw_text or not raw_text.strip():
        raise AnalysisOrchestratorError(
            "Resume has no extracted text content. Please ensure document parsing succeeded.",
            status_code=422,
        )

    # Get candidate type (default to experienced if missing)
    candidate_type = CandidateType.experienced
    if resume.candidate and resume.candidate.candidate_type:
        candidate_type = resume.candidate.candidate_type

    # Find or initialize ResumeAnalysis record (supports safe retry)
    analysis_record = db.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == resume_id).first()
    if not analysis_record:
        analysis_record = ResumeAnalysis(
            resume_id=resume_id,
            analysis_status=AnalysisStatus.pending,
        )
        db.add(analysis_record)
        db.flush()
    else:
        analysis_record.analysis_status = AnalysisStatus.pending
        analysis_record.analysis_error = None
        db.flush()

    # Step 1: Run deterministic candidate-type-aware scoring
    det_result = calculate_compatibility_score(raw_text, candidate_type=candidate_type)
    analysis_record.compatibility_score = det_result.compatibility_score
    analysis_record.section_score = det_result.section_score
    analysis_record.impact_score = det_result.impact_score
    analysis_record.formatting_score = det_result.formatting_score
    analysis_record.identified_sections = det_result.identified_sections
    analysis_record.scoring_breakdown = det_result.scoring_breakdown

    # Step 2: Run Gemini API for grounded semantic intelligence
    try:
        gemini_result = run_gemini_analysis(
            resume_text=raw_text,
            candidate_type=candidate_type,
            api_key=api_key,
        )

        effective_model = os.getenv("GEMINI_MODEL", CURRENT_MODEL_NAME)
        analysis_record.summary = gemini_result.summary

        # Deterministically ground and filter skills against original resume text
        grounded_skills, rejected_skills = ground_and_filter_skills(
            raw_skills=gemini_result.skills_categorized,
            resume_text=raw_text,
        )
        if rejected_skills:
            logger.info(
                f"Resume {resume_id} skill grounding excluded {len(rejected_skills)} unsupported skills: "
                f"{', '.join(rejected_skills[:5])}{'...' if len(rejected_skills) > 5 else ''}"
            )
        analysis_record.skills_categorized = grounded_skills

        # Normalize strengths into List[str] with evidence anchors
        formatted_strengths: list = []
        for s in gemini_result.strengths:
            if isinstance(s, str):
                formatted_strengths.append(s.strip())
            elif hasattr(s, "to_display_string"):
                formatted_strengths.append(s.to_display_string())
            elif isinstance(s, dict):
                anchor = s.get("anchor", "").strip()
                stmt = s.get("statement", "").strip()
                formatted_strengths.append(f"[{anchor}]: {stmt}" if anchor else stmt)
        analysis_record.strengths = formatted_strengths

        analysis_record.improvements = [item.model_dump() for item in gemini_result.improvements]
        analysis_record.suggested_roles = [r.strip() for r in gemini_result.suggested_roles if isinstance(r, str) and r.strip()]
        analysis_record.missing_or_uncertain_elements = [
            m.strip() for m in getattr(gemini_result, "missing_or_uncertain_elements", []) if isinstance(m, str) and m.strip()
        ]
        analysis_record.model_name = effective_model
        analysis_record.prompt_version = CURRENT_PROMPT_VERSION
        analysis_record.analysis_status = AnalysisStatus.completed
        analysis_record.analysis_error = None


    except GeminiServiceError as ge:
        effective_model = os.getenv("GEMINI_MODEL", CURRENT_MODEL_NAME)
        clean_err = mask_sensitive_data(str(ge))
        logger.warning(f"Gemini analysis encountered an error for resume {resume_id}: {clean_err}")
        analysis_record.analysis_status = AnalysisStatus.failed
        analysis_record.analysis_error = clean_err
        analysis_record.model_name = effective_model
        analysis_record.prompt_version = CURRENT_PROMPT_VERSION
        # Even if Gemini fails, deterministic scores are preserved so the user can inspect and retry
    except Exception as e:
        clean_err = mask_sensitive_data(str(e))
        logger.error(f"Unexpected error during resume analysis: {clean_err}")
        analysis_record.analysis_status = AnalysisStatus.failed
        analysis_record.analysis_error = f"Unexpected error during analysis: {clean_err}"

    db.commit()
    db.refresh(analysis_record)
    return analysis_record
