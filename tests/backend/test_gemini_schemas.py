import pytest
from pydantic import ValidationError
from app.services.gemini_service import (
    GeminiAnalysisOutput,
    GeminiImprovementSchema,
    SkillCategorizationSchema,
    StrengthItem,
)
from app.services.analysis_orchestrator import orchestrate_resume_analysis
from app.models.candidate import Candidate, CandidateType
from app.models.resume import Resume, UploadStatus
from unittest.mock import patch


def test_strength_item_validation_and_display():
    """Verify StrengthItem validates required fields and generates clean anchored display strings."""
    item = StrengthItem(
        anchor="Autonomous Rover Simulation",
        statement="Engineered A* pathfinding algorithm reducing latency by 18%.",
    )
    assert item.anchor == "Autonomous Rover Simulation"
    assert item.to_display_string() == "[Autonomous Rover Simulation]: Engineered A* pathfinding algorithm reducing latency by 18%."

    # Strips redundant square brackets if provided by model
    bracketed = StrengthItem(
        anchor="[DevPortal Project]:",
        statement="Implemented real-time WebSockets.",
    )
    assert bracketed.to_display_string() == "[DevPortal Project]: Implemented real-time WebSockets."


def test_strength_item_rejection_of_empty_strings():
    """Reject empty anchors or statements."""
    with pytest.raises(ValidationError):
        StrengthItem(anchor="", statement="Valid statement")

    with pytest.raises(ValidationError):
        StrengthItem(anchor="Valid Anchor", statement="")


def test_skill_categorization_schema_structure():
    """Verify explicit vs contextual skill classification structure."""
    skills = SkillCategorizationSchema(
        explicit={
            "Languages": ["Python", "TypeScript"],
            "Frameworks": ["FastAPI", "React"],
        },
        contextual={
            "Developer Tools": ["Git", "Docker"],
        },
    )
    assert "Python" in skills.explicit["Languages"]
    assert "Git" in skills.contextual["Developer Tools"]


def test_gemini_analysis_output_allows_empty_lists():
    """Verify that strengths and improvements are allowed to be empty lists when evidence is sparse."""
    output = GeminiAnalysisOutput(
        summary="Brief student resume overview.",
        skills_categorized=SkillCategorizationSchema(),
        strengths=[],
        improvements=[],
        suggested_roles=["Software Engineering Intern"],
        missing_or_uncertain_elements=["Missing graduation year"],
    )
    assert output.strengths == []
    assert output.improvements == []
    assert len(output.missing_or_uncertain_elements) == 1


def test_gemini_analysis_output_rejection_of_too_short_summary():
    """Summary must have reasonable minimum length (at least 5 characters)."""
    with pytest.raises(ValidationError):
        GeminiAnalysisOutput(summary="Hi")


def test_orchestrator_formats_structured_strengths_and_skills(db_session):
    """
    Verify that analysis orchestrator:
    1. Formats StrengthItem objects into anchored strings without breaking the List[str] contract.
    2. Labels explicit and contextual skills in skills_categorized.
    3. Omits empty categories.
    4. Persists missing_or_uncertain_elements.
    """
    candidate = Candidate(
        full_name="Alice Candidate",
        email="alice_test_schemas@example.com",
        candidate_type=CandidateType.student,
    )
    db_session.add(candidate)
    db_session.commit()

    resume = Resume(
        candidate_id=candidate.id,
        original_filename="alice_resume.pdf",
        file_path="/tmp/alice_resume.pdf",
        file_type="pdf",
        upload_status=UploadStatus.completed,
        extracted_text="Alice Candidate\nalice@example.com\nEducation: BS CS\nSkills: Python, React\nProjects: DevPortal using FastAPI",
    )
    db_session.add(resume)
    db_session.commit()

    mock_gemini = GeminiAnalysisOutput(
        summary="Computer science student with strong software project foundations.",
        skills_categorized=SkillCategorizationSchema(
            explicit={
                "Languages": ["Python"],
                "Frameworks": ["React"],
                "EmptyCategory": [],  # Should be omitted!
            },
            contextual={
                "Frameworks": ["FastAPI"],
            },
        ),
        strengths=[
            StrengthItem(anchor="DevPortal", statement="Built REST API with FastAPI."),
        ],
        improvements=[
            GeminiImprovementSchema(
                category="Impact",
                issue="Project descriptions lack quantifiable metrics.",
                recommendation="Add user count or performance measurements.",
                example="Before: 'Built API' -> After: 'Built API handling 100 req/s'",
            ),
        ],
        suggested_roles=["Software Engineering Intern"],
        missing_or_uncertain_elements=["Missing graduation year / expected graduation date"],
    )

    with patch("app.services.analysis_orchestrator.run_gemini_analysis", return_value=mock_gemini):
        analysis = orchestrate_resume_analysis(resume.id, db_session)

    # 1. Strengths should be List[str] with anchors
    assert len(analysis.strengths) == 1
    assert analysis.strengths[0] == "[DevPortal]: Built REST API with FastAPI."

    # 2. Skills categorized should distinguish explicit vs contextual and drop empty buckets
    assert "Languages (Explicit)" in analysis.skills_categorized
    assert analysis.skills_categorized["Languages (Explicit)"] == ["Python"]
    assert "Frameworks (Contextual)" in analysis.skills_categorized
    assert analysis.skills_categorized["Frameworks (Contextual)"] == ["FastAPI"]
    assert "EmptyCategory (Explicit)" not in analysis.skills_categorized

    # 3. Missing elements persisted
    assert len(analysis.missing_or_uncertain_elements) == 1
    assert "graduation" in analysis.missing_or_uncertain_elements[0]

