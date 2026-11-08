from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.analysis import AnalysisStatus


class ImprovementItem(BaseModel):
    category: str = Field(..., min_length=2, max_length=50, description="Area of improvement, e.g. Impact, Sections, Formatting, Skills")
    issue: str = Field(..., min_length=3, max_length=500, description="Observed issue grounded in resume content")
    recommendation: str = Field(..., min_length=3, max_length=500, description="Actionable recommendation to improve")
    example: Optional[str] = Field(default=None, max_length=500, description="Concrete example illustrating the recommended fix")



class ScoringFactor(BaseModel):
    name: str = Field(..., description="Name of the scored factor")
    score: int = Field(..., ge=0, le=100, description="Factor score out of 100")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight of this factor in the aggregate score")
    explanation: str = Field(..., description="Transparent explanation of the score and findings")


class ScoreBreakdown(BaseModel):
    candidate_type: str = Field(..., description="Candidate type evaluated (student, fresher, experienced)")
    section_factors: List[ScoringFactor] = Field(default_factory=list)
    impact_factors: List[ScoringFactor] = Field(default_factory=list)
    formatting_factors: List[ScoringFactor] = Field(default_factory=list)
    general_notes: List[str] = Field(default_factory=list)


class ResumeAnalysisBase(BaseModel):
    compatibility_score: int = Field(default=0, ge=0, le=100, description="Resume Compatibility Score (0-100)")
    section_score: int = Field(default=0, ge=0, le=100, description="Section completeness score (0-100)")
    impact_score: int = Field(default=0, ge=0, le=100, description="Measurable impact & action verb score (0-100)")
    formatting_score: int = Field(default=0, ge=0, le=100, description="Document formatting & structure score (0-100)")
    summary: Optional[str] = Field(default=None, description="Executive analysis summary")
    identified_sections: List[str] = Field(default_factory=list, description="List of recognized resume sections")
    skills_categorized: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Categorized skills verified against resume text",
    )
    strengths: List[str] = Field(default_factory=list, description="Evidence-backed candidate strengths")
    improvements: List[ImprovementItem] = Field(
        default_factory=list,
        description="Actionable improvement recommendations with examples",
    )
    suggested_roles: List[str] = Field(default_factory=list, description="Recommended matching job roles")
    missing_or_uncertain_elements: List[str] = Field(
        default_factory=list,
        description="Candidate-appropriate absent or ambiguous information observed in the resume",
    )
    scoring_breakdown: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed scoring breakdown with candidate-type context",
    )

    @field_validator(
        "identified_sections",
        "strengths",
        "improvements",
        "suggested_roles",
        "missing_or_uncertain_elements",
        mode="before",
    )
    @classmethod
    def _coerce_none_to_empty_list(cls, v: Any) -> Any:
        return [] if v is None else v

    @field_validator("skills_categorized", "scoring_breakdown", mode="before")
    @classmethod
    def _coerce_none_to_empty_dict(cls, v: Any) -> Any:
        return {} if v is None else v



class ResumeAnalysisCreate(ResumeAnalysisBase):
    resume_id: int = Field(..., gt=0, description="ID of the resume being analyzed")
    analysis_status: AnalysisStatus = Field(default=AnalysisStatus.pending)
    model_name: Optional[str] = Field(default=None)
    prompt_version: Optional[str] = Field(default=None)
    analysis_error: Optional[str] = Field(default=None)


class ResumeAnalysisUpdate(BaseModel):
    analysis_status: Optional[AnalysisStatus] = None
    compatibility_score: Optional[int] = Field(default=None, ge=0, le=100)
    section_score: Optional[int] = Field(default=None, ge=0, le=100)
    impact_score: Optional[int] = Field(default=None, ge=0, le=100)
    formatting_score: Optional[int] = Field(default=None, ge=0, le=100)
    summary: Optional[str] = None
    identified_sections: Optional[List[str]] = None
    skills_categorized: Optional[Dict[str, List[str]]] = None
    strengths: Optional[List[str]] = None
    improvements: Optional[List[ImprovementItem]] = None
    suggested_roles: Optional[List[str]] = None
    missing_or_uncertain_elements: Optional[List[str]] = None
    scoring_breakdown: Optional[Dict[str, Any]] = None

    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    analysis_error: Optional[str] = None


class ResumeAnalysisResponse(ResumeAnalysisBase):
    id: int
    resume_id: int
    analysis_status: AnalysisStatus
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    analysis_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
