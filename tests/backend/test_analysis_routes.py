import uuid
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.candidate import Candidate, CandidateType
from app.models.resume import Resume, UploadStatus
from app.services.gemini_service import GeminiAnalysisOutput, GeminiImprovementSchema, GeminiServiceError


SAMPLE_RESUME_TEXT = """
David Miller
david.miller@example.com | (555) 345-6789 | github.com/davidmiller
New York, NY

PROFESSIONAL SUMMARY
Full-Stack Developer with 3 years of experience building modern web applications with React, Node.js, and Python.

WORK EXPERIENCE
Software Developer | AlphaTech Solutions | 2022 - Present
• Designed and delivered 5 core microservices using FastAPI and PostgreSQL, decreasing API latency by 35%.
• Spearheaded frontend revamp with React and Tailwind CSS, increasing user engagement by 28%.
• Automated CI/CD pipelines via GitHub Actions, reducing release deployment time by 50%.

TECHNICAL SKILLS
Languages: Python, JavaScript, TypeScript, SQL
Frameworks: React, FastAPI, Express.js, Tailwind CSS
Databases & Tools: PostgreSQL, Docker, Git, Redis

EDUCATION
Bachelor of Science in Software Engineering, Columbia University (2022)
"""

MOCK_GEMINI_OUTPUT = GeminiAnalysisOutput(
    summary="Full-Stack Developer with 3 years of demonstrated expertise in React, FastAPI, and PostgreSQL microservices.",
    skills_categorized={
        "Languages": ["Python", "JavaScript", "TypeScript", "SQL"],
        "Frameworks & Libraries": ["React", "FastAPI", "Express.js", "Tailwind CSS"],
        "Databases & Storage": ["PostgreSQL", "Redis"],
        "Tools & Platforms": ["Docker", "Git", "GitHub Actions"],
    },
    strengths=[
        "Demonstrated performance optimization: reduced API latency by 35%.",
        "Strong full-stack breadth spanning FastAPI backends and React frontends.",
        "Production CI/CD deployment automation experience.",
    ],
    improvements=[
        GeminiImprovementSchema(
            category="Impact",
            issue="Some bullet points could describe business context or team scale.",
            recommendation="Quantify active users or transaction volumes handled by the microservices.",
            example="FastAPI services -> Serving 10,000+ daily active users",
        ),
    ],
    suggested_roles=[
        "Full-Stack Software Engineer",
        "Backend Developer (Python/FastAPI)",
        "Frontend Developer (React)",
    ],
)


@pytest.fixture
def sample_candidate(db_session: Session) -> Candidate:
    uid = uuid.uuid4().hex[:8]
    candidate = Candidate(
        full_name=f"David Miller {uid}",
        email=f"david_{uid}@example.com",
        candidate_type=CandidateType.experienced,
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    return candidate


@pytest.fixture
def sample_resume(db_session: Session, sample_candidate: Candidate) -> Resume:
    resume = Resume(
        candidate_id=sample_candidate.id,
        original_filename="david_miller_resume.pdf",
        file_path="/tmp/david_miller_resume.pdf",
        file_type="pdf",
        upload_status=UploadStatus.completed,
        extracted_text=SAMPLE_RESUME_TEXT,
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)
    return resume


def test_analyze_resume_success(client: TestClient, sample_resume: Resume):
    """Test full analysis flow with mocked Gemini API."""
    with patch("app.services.analysis_orchestrator.run_gemini_analysis", return_value=MOCK_GEMINI_OUTPUT):
        response = client.post(f"/api/resumes/{sample_resume.id}/analyze")

    assert response.status_code == 200
    data = response.json()

    assert data["resume_id"] == sample_resume.id
    assert data["analysis_status"] == "completed"
    assert data["compatibility_score"] >= 70
    assert data["section_score"] >= 80
    assert data["impact_score"] >= 60
    assert data["formatting_score"] >= 80

    # AI-extracted content
    assert "Languages" in data["skills_categorized"]
    assert len(data["strengths"]) == 3
    assert len(data["improvements"]) == 1
    assert data["improvements"][0]["category"] == "Impact"
    assert len(data["suggested_roles"]) == 3
    assert data["analysis_error"] is None



def test_get_resume_analysis(client: TestClient, sample_resume: Resume):
    """Test retrieving existing resume analysis."""
    with patch("app.services.analysis_orchestrator.run_gemini_analysis", return_value=MOCK_GEMINI_OUTPUT):
        client.post(f"/api/resumes/{sample_resume.id}/analyze")

    get_resp = client.get(f"/api/resumes/{sample_resume.id}/analysis")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["resume_id"] == sample_resume.id
    assert data["analysis_status"] == "completed"
    assert data["compatibility_score"] >= 80


def test_get_nonexistent_analysis(client: TestClient):
    """Test 404 when querying analysis that does not exist."""
    response = client.get("/api/resumes/99999/analysis")
    assert response.status_code == 404
    assert "No analysis found" in response.json()["detail"]


def test_analyze_resume_without_extracted_text(client: TestClient, db_session: Session, sample_candidate: Candidate):
    """Test 422 when resume has no extracted text."""
    empty_resume = Resume(
        candidate_id=sample_candidate.id,
        original_filename="empty.pdf",
        file_path="/tmp/empty.pdf",
        file_type="pdf",
        upload_status=UploadStatus.completed,
        extracted_text="",
    )
    db_session.add(empty_resume)
    db_session.commit()
    db_session.refresh(empty_resume)

    response = client.post(f"/api/resumes/{empty_resume.id}/analyze")
    assert response.status_code == 422
    assert "no extracted text" in response.json()["detail"]


def test_analyze_gemini_failure_and_safe_retry(client: TestClient, sample_resume: Resume):
    """Test graceful handling of Gemini failure, followed by successful retry."""
    # 1. First attempt fails due to simulated API rate limit
    with patch("app.services.analysis_orchestrator.run_gemini_analysis", side_effect=GeminiServiceError("API rate limit exceeded")):
        response = client.post(f"/api/resumes/{sample_resume.id}/analyze")

    assert response.status_code == 200
    failed_data = response.json()
    assert failed_data["analysis_status"] == "failed"
    assert "API rate limit exceeded" in failed_data["analysis_error"]
    # Deterministic scoring is still present!
    assert failed_data["compatibility_score"] >= 70

    # 2. Safe retry succeeds
    with patch("app.services.analysis_orchestrator.run_gemini_analysis", return_value=MOCK_GEMINI_OUTPUT):
        retry_response = client.post(f"/api/resumes/{sample_resume.id}/analyze")

    assert retry_response.status_code == 200
    success_data = retry_response.json()
    assert success_data["analysis_status"] == "completed"
    assert success_data["analysis_error"] is None
    assert len(success_data["strengths"]) == 3
