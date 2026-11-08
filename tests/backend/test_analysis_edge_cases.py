"""
P0 Edge-Case and Reliability Tests for ResumeIQ Analysis Pipeline (Phase 6.2.4).

Covers:
1. Empty Gemini output database/API roundtrip.
2. Preserving deterministic scores when Gemini fails.
3. Sequential analysis retry idempotency (exactly one analysis record).
4. Legacy database record deserialization and API compatibility.
"""

import time
import pytest
from unittest.mock import patch

from app.models.analysis import AnalysisStatus, ResumeAnalysis
from app.models.candidate import Candidate, CandidateType
from app.models.resume import Resume, UploadStatus
from app.services.gemini_service import (
    GeminiAnalysisOutput,
    GeminiImprovementSchema,
    GeminiServiceError,
    SkillCategorizationSchema,
    StrengthItem,
    build_analysis_prompt,
)
from app.services.scoring_engine import calculate_compatibility_score
from app.services.skill_grounding import (
    ground_and_filter_skills,
    verify_contextual_skill,
    verify_explicit_skill,
)


SAMPLE_RESUME_TEXT = """
Jane Doe
jane.doe@example.com | (555) 345-6789 | github.com/janedoe
San Francisco, CA

PROFESSIONAL SUMMARY
Full-Stack Software Engineer with 4 years of experience building scalable web applications.

WORK EXPERIENCE
Software Engineer | Apex Systems | 2021 - Present
• Designed and developed 4 core REST API services using Python and FastAPI, reducing latency by 30%.
• Containerized microservices using Docker and deployed onto AWS cloud infrastructure.
• Collaborated with frontend team to build responsive interfaces with React and Tailwind CSS.

TECHNICAL SKILLS
Languages: Python, JavaScript, TypeScript, SQL
Frameworks: FastAPI, React, Express.js
Tools: Docker, Git, AWS

EDUCATION
Bachelor of Science in Computer Science, University of California (2021)
"""


def test_empty_gemini_output_database_and_api_roundtrip(client, db_session):
    """
    P0.1: Verify that when Gemini returns valid empty lists/dicts for all structured fields,
    the orchestrator and database persist them cleanly and the API responds with HTTP 200.
    """
    candidate = Candidate(
        full_name="Minimal Candidate",
        email="minimal_empty_test@example.com",
        candidate_type=CandidateType.student,
    )
    db_session.add(candidate)
    db_session.commit()

    resume = Resume(
        candidate_id=candidate.id,
        original_filename="minimal_resume.pdf",
        file_path="/tmp/minimal_resume.pdf",
        file_type="pdf",
        upload_status=UploadStatus.completed,
        extracted_text="Jane Student\njane@example.com\nEducation: BS CS\nProjects: Personal Website",
    )
    db_session.add(resume)
    db_session.commit()

    empty_gemini_output = GeminiAnalysisOutput(
        summary="Candidate possesses foundational coursework and early project experience.",
        skills_categorized=SkillCategorizationSchema(explicit={}, contextual={}),
        strengths=[],
        improvements=[],
        suggested_roles=[],
        missing_or_uncertain_elements=[],
    )

    with patch("app.services.analysis_orchestrator.run_gemini_analysis", return_value=empty_gemini_output):
        response = client.post(f"/api/resumes/{resume.id}/analyze")

    assert response.status_code == 200
    data = response.json()

    assert data["analysis_status"] == "completed"
    assert data["summary"] == "Candidate possesses foundational coursework and early project experience."
    assert data["skills_categorized"] == {}
    assert data["strengths"] == []
    assert data["improvements"] == []
    assert data["suggested_roles"] == []
    assert data["missing_or_uncertain_elements"] == []

    # GET endpoint retrieval verification
    get_resp = client.get(f"/api/resumes/{resume.id}/analysis")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["skills_categorized"] == {}
    assert get_data["strengths"] == []
    assert get_data["improvements"] == []
    assert get_data["suggested_roles"] == []
    assert get_data["missing_or_uncertain_elements"] == []

    # Direct database check
    db_record = db_session.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == resume.id).first()
    assert db_record is not None
    assert db_record.analysis_status == AnalysisStatus.completed
    assert db_record.strengths == []
    assert db_record.skills_categorized == {}
    assert db_record.improvements == []
    assert db_record.suggested_roles == []
    assert db_record.missing_or_uncertain_elements == []


def test_preserve_deterministic_scores_when_gemini_fails(client, db_session):
    """
    P0.2: Verify that when Gemini API invocation fails (e.g. rate limit, 503, network drop),
    the deterministic scores (compatibility, sections, impact, formatting, scoring_breakdown)
    are fully computed, preserved, and retrievable via GET /api/resumes/{id}/analysis.
    """
    candidate = Candidate(
        full_name="Reliable Candidate",
        email="reliable_failure_test@example.com",
        candidate_type=CandidateType.experienced,
    )
    db_session.add(candidate)
    db_session.commit()

    resume = Resume(
        candidate_id=candidate.id,
        original_filename="reliable_resume.pdf",
        file_path="/tmp/reliable_resume.pdf",
        file_type="pdf",
        upload_status=UploadStatus.completed,
        extracted_text=SAMPLE_RESUME_TEXT,
    )
    db_session.add(resume)
    db_session.commit()

    # Simulate Gemini outage
    with patch(
        "app.services.analysis_orchestrator.run_gemini_analysis",
        side_effect=GeminiServiceError("Upstream Gemini 503: The model is overloaded. Please try again later."),
    ):
        post_resp = client.post(f"/api/resumes/{resume.id}/analyze")

    assert post_resp.status_code == 200
    post_data = post_resp.json()

    # Status must be failed with the error message
    assert post_data["analysis_status"] == "failed"
    assert "Upstream Gemini 503" in post_data["analysis_error"]

    # CRITICAL: Deterministic scores must NOT be zeroed out
    assert post_data["compatibility_score"] >= 60
    assert post_data["section_score"] >= 70
    assert post_data["impact_score"] >= 50
    assert post_data["formatting_score"] >= 70
    assert len(post_data["identified_sections"]) >= 3
    assert "Education" in post_data["identified_sections"]
    assert "Skills" in post_data["identified_sections"]

    breakdown = post_data["scoring_breakdown"]
    assert breakdown["candidate_type"] == "experienced"
    assert len(breakdown["section_factors"]) > 0
    assert len(breakdown["impact_factors"]) > 0

    # GET endpoint must also return the failed record with preserved scores
    get_resp = client.get(f"/api/resumes/{resume.id}/analysis")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["analysis_status"] == "failed"
    assert get_data["compatibility_score"] == post_data["compatibility_score"]
    assert get_data["section_score"] == post_data["section_score"]
    assert get_data["scoring_breakdown"]["candidate_type"] == "experienced"


def test_sequential_analysis_retry_idempotency(client, db_session):
    """
    P0.3: Verify that multiple sequential analyze requests on the same resume:
    1. Maintain exactly ONE ResumeAnalysis row in the database.
    2. Keep the primary key id stable.
    3. Transition cleanly from failed to completed upon retry.
    4. Clear previous error messages when retry succeeds.
    """
    candidate = Candidate(
        full_name="Retry Candidate",
        email="retry_idempotency_test@example.com",
        candidate_type=CandidateType.experienced,
    )
    db_session.add(candidate)
    db_session.commit()

    resume = Resume(
        candidate_id=candidate.id,
        original_filename="retry_resume.pdf",
        file_path="/tmp/retry_resume.pdf",
        file_type="pdf",
        upload_status=UploadStatus.completed,
        extracted_text=SAMPLE_RESUME_TEXT,
    )
    db_session.add(resume)
    db_session.commit()

    # Step 1: First attempt fails
    with patch(
        "app.services.analysis_orchestrator.run_gemini_analysis",
        side_effect=GeminiServiceError("Transient network timeout."),
    ):
        resp1 = client.post(f"/api/resumes/{resume.id}/analyze")

    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["analysis_status"] == "failed"
    assert data1["analysis_error"] is not None
    initial_analysis_id = data1["id"]

    # Verify exactly 1 DB row exists
    records_count_1 = db_session.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == resume.id).count()
    assert records_count_1 == 1

    # Step 2: Second attempt (Retry) succeeds
    successful_mock = GeminiAnalysisOutput(
        summary="Experienced Full-Stack Engineer with Python and React expertise.",
        skills_categorized=SkillCategorizationSchema(
            explicit={"Languages": ["Python", "SQL"], "Frameworks": ["FastAPI", "React"]},
            contextual={},
        ),
        strengths=[
            StrengthItem(anchor="Apex Systems", statement="Engineered 4 core REST APIs reducing latency by 30%."),
        ],
        improvements=[],
        suggested_roles=["Senior Backend Engineer", "Full-Stack Developer"],
        missing_or_uncertain_elements=[],
    )

    with patch("app.services.analysis_orchestrator.run_gemini_analysis", return_value=successful_mock):
        resp2 = client.post(f"/api/resumes/{resume.id}/analyze")

    assert resp2.status_code == 200
    data2 = resp2.json()

    # Must transition to completed with cleared error
    assert data2["analysis_status"] == "completed"
    assert data2["analysis_error"] is None
    assert data2["id"] == initial_analysis_id  # Stable primary key!
    assert "Languages (Explicit)" in data2["skills_categorized"]

    # Verify DB still has exactly 1 record
    records_count_2 = db_session.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == resume.id).count()
    assert records_count_2 == 1

    # Step 3: Third attempt (Force re-run) also succeeds idempotently
    with patch("app.services.analysis_orchestrator.run_gemini_analysis", return_value=successful_mock):
        resp3 = client.post(f"/api/resumes/{resume.id}/analyze", json={"force_refresh": True})

    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["id"] == initial_analysis_id
    records_count_3 = db_session.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == resume.id).count()
    assert records_count_3 == 1


def test_legacy_database_record_deserialization_compatibility(client, db_session):
    """
    P0.4: Verify that legacy database records (from before Phase 6.2.2/6.2.3) with:
    - Flat skills_categorized (no (Explicit) or (Contextual) tags)
    - Plain string strengths (no [Anchor]: format)
    - NULL or missing missing_or_uncertain_elements
    - Optional improvement fields as None
    deserialize cleanly via GET /api/resumes/{id}/analysis without Pydantic validation errors.
    """
    candidate = Candidate(
        full_name="Legacy Candidate",
        email="legacy_compat_test@example.com",
        candidate_type=CandidateType.experienced,
    )
    db_session.add(candidate)
    db_session.commit()

    resume = Resume(
        candidate_id=candidate.id,
        original_filename="legacy_resume.pdf",
        file_path="/tmp/legacy_resume.pdf",
        file_type="pdf",
        upload_status=UploadStatus.completed,
        extracted_text=SAMPLE_RESUME_TEXT,
    )
    db_session.add(resume)
    db_session.commit()

    # Manually insert a legacy record directly into the DB session
    legacy_record = ResumeAnalysis(
        resume_id=resume.id,
        analysis_status=AnalysisStatus.completed,
        compatibility_score=82,
        section_score=85,
        impact_score=78,
        formatting_score=84,
        summary="Legacy summary from Phase 1-5 without modern schema constraints.",
        identified_sections=["Summary", "Experience", "Skills", "Education"],
        # Legacy flat skills format
        skills_categorized={
            "Languages": ["Python", "JavaScript"],
            "Databases": ["PostgreSQL"],
        },
        # Legacy non-anchored plain string strengths
        strengths=[
            "Demonstrated microservices optimization reducing latency.",
            "Strong team collaboration across frontend and backend.",
        ],
        # Improvements with None for example
        improvements=[
            {
                "category": "Impact",
                "issue": "Some bullets lack quantified metrics.",
                "recommendation": "Add percentage improvements or throughput numbers.",
                "example": None,
            }
        ],
        suggested_roles=["Senior Backend Engineer", "Full-Stack Developer"],
        # Legacy record where missing_or_uncertain_elements is None/NULL
        missing_or_uncertain_elements=None,
        scoring_breakdown={
            "candidate_type": "experienced",
            "section_factors": [],
            "impact_factors": [],
            "formatting_factors": [],
        },
    )
    db_session.add(legacy_record)
    db_session.commit()

    # Fetch through the FastAPI GET endpoint
    response = client.get(f"/api/resumes/{resume.id}/analysis")

    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
    data = response.json()

    # 1. Legacy flat skills preserved
    assert "Languages" in data["skills_categorized"]
    assert data["skills_categorized"]["Languages"] == ["Python", "JavaScript"]
    assert "Databases" in data["skills_categorized"]

    # 2. Legacy non-anchored strengths preserved as strings
    assert len(data["strengths"]) == 2
    assert "Demonstrated microservices" in data["strengths"][0]

    # 3. None for missing_or_uncertain_elements safely coerced to empty list
    assert data["missing_or_uncertain_elements"] == []

    # 4. Improvements with example=None preserved
    assert len(data["improvements"]) == 1
    assert data["improvements"][0]["category"] == "Impact"
    assert data["improvements"][0]["example"] is None


# ============================================================================
# P1: Quality & Fairness Tests
# ============================================================================

def test_candidate_tier_scoring_fairness():
    """
    P1.1: Verify documented candidate-tier scoring rules:
    - Student: metric leniency (1 metric scores 80), experience optional (bonus only).
    - Fresher: balanced metrics (1 metric scores 65), experience weighted at 10%.
    - Experienced: high metric requirement (1 metric scores 55), work experience weighted at 35%.
    On an entry-level project resume without commercial work experience,
    student and fresher receive fairer scores than an experienced profile.
    """
    entry_level_resume = """
Alex Chen
alex.chen@example.edu | (555) 234-5678 | github.com/alexchen
San Francisco, CA

EDUCATION
Bachelor of Science in Computer Science
State University (2024)

TECHNICAL SKILLS
Python, JavaScript, React, FastAPI, SQL, Git

PROJECTS
• Campus Connect Platform
  - Developed full-stack web application using React and FastAPI.
  - Implemented database queries in SQL and optimized indexing.
  - Automated deployment workflows using GitHub Actions.
  - Built real-time notifications, improving response speed by 15%.
"""
    student_res = calculate_compatibility_score(entry_level_resume, CandidateType.student)
    fresher_res = calculate_compatibility_score(entry_level_resume, CandidateType.fresher)
    exp_res = calculate_compatibility_score(entry_level_resume, CandidateType.experienced)

    # 1. Section score fairness:
    # Student requires Education + Projects + Skills + Contact (gets 100)
    # Experienced requires Work Experience (0.35 weight) and drops significantly
    assert student_res.section_score > exp_res.section_score
    assert fresher_res.section_score > exp_res.section_score

    # 2. Metric impact score fairness:
    # 1 metric: student gets 80, fresher gets 65, experienced gets 55
    student_metric_factor = next(f for f in student_res.scoring_breakdown["impact_factors"] if f["name"] == "Measurable Metrics & Impact")
    fresher_metric_factor = next(f for f in fresher_res.scoring_breakdown["impact_factors"] if f["name"] == "Measurable Metrics & Impact")
    exp_metric_factor = next(f for f in exp_res.scoring_breakdown["impact_factors"] if f["name"] == "Measurable Metrics & Impact")

    assert student_metric_factor["score"] == 80
    assert fresher_metric_factor["score"] == 65
    assert exp_metric_factor["score"] == 55

    # 3. Overall compatibility score reflects documented tier expectations
    assert student_res.compatibility_score > exp_res.compatibility_score
    assert fresher_res.compatibility_score > exp_res.compatibility_score

    # 4. Breakdown candidate_type accurately identifies each profile
    assert student_res.scoring_breakdown["candidate_type"] == "student"
    assert fresher_res.scoring_breakdown["candidate_type"] == "fresher"
    assert exp_res.scoring_breakdown["candidate_type"] == "experienced"


def test_candidate_specific_prompt_calibration():
    """
    P1.2: Verify build_analysis_prompt generates strict candidate-level instructions:
    - Student: student-level opportunities (Intern, Research Assistant), no penalty for lacking commercial experience.
    - Fresher: graduate & entry-level roles (Associate, Junior Backend, Graduate Trainee).
    - Experienced: mid/senior/lead roles, scrutinizing business and technical scale metrics.
    """
    text = "Jane Candidate\njane@example.com\nSkills: Python, React"

    prompt_student = build_analysis_prompt(text, CandidateType.student)
    assert "CANDIDATE TYPE: STUDENT" in prompt_student
    assert "Software Engineering Intern" in prompt_student
    assert "Research Assistant" in prompt_student
    assert "Do NOT penalize the student for lacking commercial work experience" in prompt_student

    prompt_fresher = build_analysis_prompt(text, CandidateType.fresher)
    assert "CANDIDATE TYPE: FRESHER" in prompt_fresher
    assert "Associate Software Engineer" in prompt_fresher
    assert "Junior Backend Developer" in prompt_fresher
    assert "Graduate Trainee" in prompt_fresher

    prompt_exp = build_analysis_prompt(text, CandidateType.experienced)
    assert "CANDIDATE TYPE: EXPERIENCED PROFESSIONAL" in prompt_exp
    assert "mid-level, senior, or lead roles" in prompt_exp
    assert "Scrutinize professional work history" in prompt_exp


def test_missing_sections_and_single_section_resumes():
    """
    P1.3: Verify scoring engine and skill grounding behavior on resumes with missing sections:
    - Experienced candidate missing Work Experience (heavy section penalty, but no crash).
    - Resume missing Education section (graceful scoring).
    - Resume missing Skills section (skills extracted inline from project bullets).
    - Single-section resume (graceful handling, no ZeroDivisionError).
    """
    # 1. Missing Work Experience on Experienced candidate
    text_no_exp = (
        "Jane Doe\njane@example.com | (555) 123-4567\n"
        "EDUCATION\nBS in Computer Science\n"
        "SKILLS\nPython, Docker\n"
        "SUMMARY\nDeveloper seeking opportunities."
    )
    res_no_exp = calculate_compatibility_score(text_no_exp, CandidateType.experienced)
    assert "Experience" not in res_no_exp.identified_sections
    exp_factor = next(f for f in res_no_exp.scoring_breakdown["section_factors"] if f["name"] == "Work Experience")
    assert exp_factor["score"] == 0
    assert res_no_exp.section_score <= 65

    # 2. Missing Education section
    text_no_edu = (
        "Jane Doe\njane@example.com | (555) 123-4567\n"
        "WORK EXPERIENCE\nSoftware Engineer | 2020 - Present\n• Built APIs with Python.\n"
        "SKILLS\nPython, FastAPI\n"
        "SUMMARY\nSelf-taught developer."
    )
    res_no_edu = calculate_compatibility_score(text_no_edu, CandidateType.experienced)
    assert "Education" not in res_no_edu.identified_sections
    edu_factor = next(f for f in res_no_edu.scoring_breakdown["section_factors"] if f["name"] == "Education")
    assert edu_factor["score"] == 0
    assert res_no_edu.compatibility_score > 0

    # 3. Resume with NO dedicated Skills header (skills mentioned only inline in projects)
    text_inline_skills = (
        "John Doe\njohn@example.com | (555) 111-2222\n"
        "PROJECTS\n"
        "• Built high-performance microservices using FastAPI, Redis, and PostgreSQL deployed with Docker."
    )
    res_inline = calculate_compatibility_score(text_inline_skills, CandidateType.student)
    assert "Skills" not in res_inline.identified_sections
    # Grounding engine still deterministically verifies explicit skills from text:
    assert verify_explicit_skill("FastAPI", text_inline_skills) is True
    assert verify_explicit_skill("Redis", text_inline_skills) is True
    assert verify_explicit_skill("PostgreSQL", text_inline_skills) is True
    assert verify_explicit_skill("Docker", text_inline_skills) is True

    # 4. Single-section resume (Contact + Summary only)
    single_sec = "Jane Doe\njane@example.com | (555) 000-1111\nSUMMARY\nAspiring developer looking for opportunities."
    res_single = calculate_compatibility_score(single_sec, CandidateType.fresher)
    assert res_single.identified_sections == ["Summary"]
    assert res_single.compatibility_score < 50
    assert res_single.section_score < 40


def test_multiline_contextual_evidence_normalization():
    """
    P1.4: Verify contextual evidence matching when excerpt spans multiple lines
    with irregular indentation, tabs, or line breaks in resume text.
    """
    multiline_resume = (
        "WORK EXPERIENCE\n"
        "Software Engineer | CloudScale Inc.\n"
        "• Architected scalable microservices\n"
        "  using FastAPI and Redis\n"
        "  to handle 50,000 requests per minute with low latency.\n"
        "• Containerized application services\n"
        "  using Docker multi-stage builds\n"
        "  and managed deployment pipelines."
    )

    # Excerpt has different line wrapping / whitespace
    evidence_multiline = "Architected scalable microservices\n  using FastAPI and Redis"
    assert verify_contextual_skill("FastAPI", evidence_multiline, multiline_resume) is True
    assert verify_contextual_skill("Redis", evidence_multiline, multiline_resume) is True

    evidence_docker = "Containerized application services\nusing Docker multi-stage builds"
    assert verify_contextual_skill("Docker", evidence_docker, multiline_resume) is True


# ============================================================================
# P2: Robustness & Stress Tests
# ============================================================================

def test_large_resume_stress_test_5000_words():
    """
    P2.5: Stress-test scoring engine and skill grounding with a large (~5,000 words) multi-page resume.
    Verifies that regex processing completes without catastrophic backtracking.
    """
    base_block = (
        "Senior Software Engineer | GlobalEnterprise (2018 - 2024)\n"
        "• Spearheaded migration of legacy monolith to microservices using FastAPI, PostgreSQL, and Redis.\n"
        "• Architected distributed services and engineered high-throughput event processing pipelines.\n"
        "• Optimized database indexing and query latency, achieving a 45% reduction in response times.\n"
        "• Containerized services with Docker and deployed across Kubernetes clusters managing $2.5M throughput.\n"
        "• Mentored 12 junior engineers and established automated CI/CD pipelines with GitHub Actions.\n"
        "• Streamlined release cycles, published technical documentation, and reduced incident recovery time by 35%.\n"
    )
    large_text = (
        "Executive Resume\n"
        "lead.engineer@enterprise.com | (555) 999-8888 | linkedin.com/in/lead-engineer\n"
        "PROFESSIONAL SUMMARY\n" + ("Extensive leadership experience in scalable distributed systems. " * 30) + "\n"
        "TECHNICAL SKILLS\n"
        "Languages: Python, Go, Rust, Java, TypeScript, SQL\n"
        "Tools: Docker, Kubernetes, AWS, Terraform, Redis, PostgreSQL\n"
        "EXPERIENCE\n" + (base_block * 50) + "\n"
        "EDUCATION\n"
        "Master of Science in Computer Science, Tech Institute (2018)\n"
    )
    word_count = len(large_text.split())
    assert word_count >= 3000

    start_t = time.perf_counter()
    res = calculate_compatibility_score(large_text, CandidateType.experienced)
    elapsed = time.perf_counter() - start_t

    # Must complete cleanly with expected scores
    assert res.compatibility_score >= 80
    assert res.detected_verbs_count >= 10
    assert res.detected_metrics_count >= 6

    # Diagnostic timing check (benchmark verification)
    assert elapsed < 3.0, f"Scoring engine took too long ({elapsed:.3f}s) on large document"

    # Skill grounding stress check on large document
    skills_to_test = {
        "explicit": {
            "Languages": ["Python", "Go", "Rust", "Java", "SQL"],
            "Tools": ["Docker", "Kubernetes", "AWS", "Terraform", "Redis", "PostgreSQL"],
        }
    }
    grounded, rejected = ground_and_filter_skills(skills_to_test, large_text)
    assert "Languages (Explicit)" in grounded
    assert "Tools (Explicit)" in grounded
    assert "Python" in grounded["Languages (Explicit)"]
    assert "Docker" in grounded["Tools (Explicit)"]
    assert len(rejected) == 0


def test_unicode_smart_quotes_non_breaking_spaces_and_bullets():
    """
    P2.6: Verify scoring engine and skill grounding with non-standard formatting:
    non-breaking spaces, smart quotes, em-dashes, and unusual bullet glyphs.
    """
    unicode_resume = (
        "José Pérez\n"
        "jose.perez@example.com\u00a0|\u00a0(555)\u00a0123-4567\u00a0|\u00a0github.com/jose-dev\n"
        "San Francisco, CA\n\n"
        "PROFESSIONAL SUMMARY\n"
        "Software engineer with ‘proven’ track record in “FastAPI” & “React”.\n\n"
        "EXPERIENCE\n"
        "Backend Developer — CloudTech (2021–Present)\n"
        "▪ Engineered 3 RESTful microservices using Python and PostgreSQL.\n"
        "► Reduced p99 latency by 35% across all endpoints.\n"
        "● Containerized microservices with Docker.\n"
        "★ Automated CI/CD deployments using GitHub Actions.\n"
        "✔ Collaborated with frontend team.\n\n"
        "TECHNICAL SKILLS\n"
        "Languages: Python, JavaScript, TypeScript, SQL\n"
        "Frameworks: FastAPI, React\n"
        "Tools: Docker, Git\n\n"
        "EDUCATION\n"
        "Bachelor of Science in Software Engineering (2021)\n"
    )
    res = calculate_compatibility_score(unicode_resume, CandidateType.experienced)
    assert res.has_email is True
    assert res.has_phone is True
    assert res.has_links is True
    assert res.detected_verbs_count >= 4
    assert res.detected_metrics_count >= 1

    # Skills extracted despite smart quotes and exotic bullets
    assert verify_explicit_skill("FastAPI", unicode_resume) is True
    assert verify_explicit_skill("Python", unicode_resume) is True
    assert verify_explicit_skill("Docker", unicode_resume) is True
    assert verify_explicit_skill("PostgreSQL", unicode_resume) is True


def test_two_column_scrambled_extraction_text():
    """
    P2.7: Verify scoring engine and skill grounding gracefully handle text from
    scrambled two-column PDF extractions without exceptions.
    """
    scrambled_text = (
        "John Smith john.smith@example.com (555) 321-4321 github.com/johnsmith\n"
        "Summary Skills Work Experience Education\n"
        "Full-stack engineer Python, React Senior Developer BS Computer Science\n"
        "Built cloud platforms FastAPI, Docker Apex Innovations State University\n"
        "Engineered microservices and reduced API latency by 25% with PostgreSQL.\n"
    )
    res = calculate_compatibility_score(scrambled_text, CandidateType.experienced)
    assert res.compatibility_score > 0
    assert res.has_email is True
    assert res.has_phone is True

    # Grounding verifies skills despite interleaved text
    assert verify_explicit_skill("Python", scrambled_text) is True
    assert verify_explicit_skill("FastAPI", scrambled_text) is True
    assert verify_explicit_skill("React", scrambled_text) is True
    assert verify_explicit_skill("Docker", scrambled_text) is True
    assert verify_explicit_skill("PostgreSQL", scrambled_text) is True


def test_versioned_and_numeric_skills():
    """
    P2.8: Verify explicit skill matching handles versioned and numeric skill declarations:
    Python 3.12, Angular 17, C++20, HTML5, CSS3.
    """
    versioned_resume = (
        "Jane Developer\njane@example.com | (555) 789-0123\n"
        "TECHNICAL SKILLS\n"
        "Languages: Python 3.12, modern C++20, ECMAScript 6\n"
        "Frameworks: Angular 17, React 18\n"
        "Web: HTML5, CSS3, Tailwind CSS\n"
        "EXPERIENCE\n"
        "• Developed frontend client with Angular 17 and HTML5/CSS3.\n"
        "• Built high-performance numerical algorithms using C++20 and Python 3.12.\n"
    )

    # 1. Exact versioned skill verification
    assert verify_explicit_skill("Python 3.12", versioned_resume) is True
    assert verify_explicit_skill("Angular 17", versioned_resume) is True
    assert verify_explicit_skill("C++20", versioned_resume) is True
    assert verify_explicit_skill("HTML5", versioned_resume) is True
    assert verify_explicit_skill("CSS3", versioned_resume) is True

    # 2. Canonical base skills matched when versioned text is present
    assert verify_explicit_skill("Python", versioned_resume) is True
    assert verify_explicit_skill("Angular", versioned_resume) is True
    assert verify_explicit_skill("C++", versioned_resume) is True
    assert verify_explicit_skill("HTML", versioned_resume) is True
    assert verify_explicit_skill("CSS", versioned_resume) is True


