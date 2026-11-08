"""
Unit and integration tests for Evidence-Based Skill Grounding (Phase 6.2.3).
"""

import pytest
from pydantic import ValidationError
from unittest.mock import patch

from app.models.candidate import Candidate, CandidateType
from app.models.resume import Resume, UploadStatus
from app.schemas.analysis import ResumeAnalysisBase
from app.services.analysis_orchestrator import orchestrate_resume_analysis
from app.services.gemini_service import (
    ContextualSkillItem,
    GeminiAnalysisOutput,
    GeminiImprovementSchema,
    SkillCategorizationSchema,
    StrengthItem,
)
from app.services.skill_grounding import (
    check_substantive_support,
    ground_and_filter_skills,
    normalize_whitespace,
    verify_contextual_skill,
    verify_explicit_skill,
)


def test_explicit_direct_matches():
    """Verify standard programming languages, tools, and frameworks with exact or case-insensitive matches."""
    text = "Experienced software engineer proficient in Python, FastAPI, Docker, and PostgreSQL."
    assert verify_explicit_skill("Python", text) is True
    assert verify_explicit_skill("fastapi", text) is True
    assert verify_explicit_skill("Docker", text) is True
    assert verify_explicit_skill("PostgreSQL", text) is True

    # Punctuation-bearing skills
    text_special = "Skills: C++, C#, .NET, Node.js, and CI/CD pipelines."
    assert verify_explicit_skill("C++", text_special) is True
    assert verify_explicit_skill("C#", text_special) is True
    assert verify_explicit_skill(".NET", text_special) is True
    assert verify_explicit_skill("Node.js", text_special) is True
    assert verify_explicit_skill("CI/CD", text_special) is True

    # Non-matches
    assert verify_explicit_skill("Rust", text) is False
    assert verify_explicit_skill("Kubernetes", text) is False
    assert verify_explicit_skill("Ruby", text) is False


def test_alias_matches_and_non_matches():
    """Verify alias mapping identifies technology synonyms and prevents cross-technology false matches."""
    text = "Built backend services using Postgres, K8s clusters, and NodeJS with JS/TS."

    # Aliases
    assert verify_explicit_skill("PostgreSQL", text) is True  # 'Postgres' in text
    assert verify_explicit_skill("Kubernetes", text) is True  # 'K8s' in text
    assert verify_explicit_skill("Node.js", text) is True  # 'NodeJS' in text
    assert verify_explicit_skill("JavaScript", text) is True  # 'JS' in text
    assert verify_explicit_skill("TypeScript", text) is True  # 'TS' in text

    # False matches must be prevented (e.g. Java in text should not match JavaScript)
    text_java = "Core Java developer specializing in Spring Boot microservices."
    assert verify_explicit_skill("Java", text_java) is True
    assert verify_explicit_skill("JavaScript", text_java) is False

    text_py = "Used Python scripts for routine file automation."
    assert verify_explicit_skill("PyTorch", text_py) is False


def test_short_and_ambiguous_skill_safeguards():
    """Verify that short names (Go, C, R, TS) do not produce false-positive matches on general words."""
    # 1. 'Go' safeguards
    text_false_go = "I like to go fast and have good problem solving skills with algorithms."
    assert verify_explicit_skill("Go", text_false_go) is False

    text_valid_go_list = "Technical Skills: Python, Go, Rust, and SQL"
    assert verify_explicit_skill("Go", text_valid_go_list) is True

    text_valid_golang = "Backend engineer with 2 years of Golang development experience."
    assert verify_explicit_skill("Go", text_valid_golang) is True

    # 2. 'C' safeguards
    text_false_c = "Experienced in critical thinking and computer concepts."
    assert verify_explicit_skill("C", text_false_c) is False

    text_valid_c = "Languages: C, C++, and Python"
    assert verify_explicit_skill("C", text_valid_c) is True

    text_valid_c_prog = "Developed embedded firmware in C programming language."
    assert verify_explicit_skill("C", text_valid_c_prog) is True

    # 3. 'R' safeguards
    text_false_r = "Responsible for research and requirement analysis."
    assert verify_explicit_skill("R", text_false_r) is False

    text_valid_r = "Performed statistical data modeling using R and Python."
    assert verify_explicit_skill("R", text_valid_r) is True

    text_valid_rstudio = "Created data visualizations using RStudio."
    assert verify_explicit_skill("R", text_valid_rstudio) is True

    # 4. 'TS' safeguards
    text_false_ts = "Managed sprint timelines on Jira tickets."
    assert verify_explicit_skill("TS", text_false_ts) is False

    text_valid_ts = "Frontend: React, TypeScript, and Tailwind CSS."
    assert verify_explicit_skill("TS", text_valid_ts) is True


def test_valid_contextual_evidence():
    """Verify contextual skills are accepted when snippet is verbatim and substantively supports the skill."""
    resume_text = (
        "WORK EXPERIENCE\n"
        "Software Engineer | CloudCorp (2022 - Present)\n"
        "• Architected RESTful microservices with FastAPI handling 50k requests daily.\n"
        "• Containerized application services using Docker and configured CI/CD deployment pipelines.\n"
        "• Implemented global application state management with Redux Toolkit."
    )

    # REST APIs supported by "RESTful microservices with FastAPI"
    snippet_rest = "Architected RESTful microservices with FastAPI"
    assert verify_contextual_skill("REST APIs", snippet_rest, resume_text) is True

    # Docker supported by "Containerized application services using Docker"
    snippet_docker = "Containerized application services using Docker"
    assert verify_contextual_skill("Docker", snippet_docker, resume_text) is True

    # State Management supported by "state management with Redux Toolkit"
    snippet_state = "Implemented global application state management with Redux Toolkit"
    assert verify_contextual_skill("State Management", snippet_state, resume_text) is True


def test_fabricated_evidence_rejection():
    """Verify contextual skills are rejected when the evidence snippet does not exist in the resume text."""
    resume_text = "Built simple portfolio website with HTML, CSS, and basic JavaScript."
    fabricated_snippet = "Orchestrated multi-region Kubernetes cluster deployment on AWS."

    # Fabricated excerpt does not exist in resume
    assert verify_contextual_skill("Kubernetes", fabricated_snippet, resume_text) is False
    assert verify_contextual_skill("AWS", fabricated_snippet, resume_text) is False


def test_existing_evidence_without_substantive_support_rejected():
    """
    Verify that an excerpt that exists in the resume text is still REJECTED if it
    does not substantively support the claimed skill.
    """
    resume_text = (
        "WORK EXPERIENCE\n"
        "Frontend Developer | WebStudio (2023 - Present)\n"
        "• Designed and styled responsive landing pages using React and Tailwind CSS."
    )
    # The snippet exists verbatim in the resume text
    real_snippet = "Designed and styled responsive landing pages using React and Tailwind CSS"

    # But it does not substantively support AWS, Kubernetes, or Python
    assert verify_contextual_skill("AWS", real_snippet, resume_text) is False
    assert verify_contextual_skill("Kubernetes", real_snippet, resume_text) is False
    assert verify_contextual_skill("Python", real_snippet, resume_text) is False

    # However, it does substantively support React and CSS
    assert verify_contextual_skill("React", real_snippet, resume_text) is True


def test_empty_category_removal():
    """Verify that categories with no verified skills are completely omitted from the result."""
    resume_text = "Skills: Python, React, SQL"

    raw_skills = SkillCategorizationSchema(
        explicit={
            "Languages": ["Python", "SQL"],
            "Cloud Platforms": ["AWS", "GCP", "Azure"],  # None exist in text!
            "EmptyBucket": [],
        },
        contextual={
            "DevOps": [
                ContextualSkillItem(
                    skill="Kubernetes",
                    evidence="Managed Kubernetes cluster on AWS",  # Fabricated!
                )
            ]
        },
    )

    grounded, rejected = ground_and_filter_skills(raw_skills, resume_text)

    # Verified category retained
    assert "Languages (Explicit)" in grounded
    assert grounded["Languages (Explicit)"] == ["Python", "SQL"]

    # Empty and unverified categories dropped
    assert "Cloud Platforms (Explicit)" not in grounded
    assert "EmptyBucket (Explicit)" not in grounded
    assert "DevOps (Contextual)" not in grounded

    # Rejected skills logged
    assert any("AWS" in r for r in rejected)
    assert any("Kubernetes" in r for r in rejected)


def test_mixed_supported_and_unsupported_skills():
    """Verify that unsupported skills are dropped within a category while valid skills are kept."""
    resume_text = "Proficient in Python and JavaScript. Built projects using React."

    raw_skills = SkillCategorizationSchema(
        explicit={
            "Languages": ["Python", "JavaScript", "Rust", "Golang", "Ruby"],
        },
        contextual={},
    )

    grounded, rejected = ground_and_filter_skills(raw_skills, resume_text)

    assert "Languages (Explicit)" in grounded
    assert grounded["Languages (Explicit)"] == ["Python", "JavaScript"]
    assert "Rust" not in grounded["Languages (Explicit)"]
    assert "Golang" not in grounded["Languages (Explicit)"]
    assert "Ruby" not in grounded["Languages (Explicit)"]

    assert any("Rust" in r for r in rejected)


def test_deduplication_preserving_order():
    """Verify duplicate skills within a category are deduplicated while preserving order."""
    resume_text = "Skills: Python, FastAPI"

    raw_skills = {
        "explicit": {
            "Languages": ["Python", "python", "PYTHON", "Python"],
            "Frameworks": ["FastAPI", "FastAPI"],
        }
    }

    grounded, _ = ground_and_filter_skills(raw_skills, resume_text)
    assert grounded["Languages (Explicit)"] == ["Python"]
    assert grounded["Frameworks (Explicit)"] == ["FastAPI"]


def test_existing_api_contract_compatibility():
    """Verify grounded output strictly adheres to Dict[str, List[str]] contract."""
    resume_text = "Languages: Python, JavaScript. Experience: Built APIs with FastAPI."

    raw_skills = SkillCategorizationSchema(
        explicit={
            "Languages": ["Python", "JavaScript"],
        },
        contextual={
            "Frameworks": [
                ContextualSkillItem(
                    skill="FastAPI",
                    evidence="Built APIs with FastAPI",
                )
            ]
        },
    )

    grounded, _ = ground_and_filter_skills(raw_skills, resume_text)

    # Must be standard dict
    assert isinstance(grounded, dict)
    for cat_name, skill_list in grounded.items():
        assert isinstance(cat_name, str)
        assert isinstance(skill_list, list)
        for s in skill_list:
            assert isinstance(s, str)

    # Must pass Pydantic schema validation for ResumeAnalysisBase
    base_model = ResumeAnalysisBase(
        compatibility_score=85,
        section_score=90,
        impact_score=80,
        formatting_score=85,
        skills_categorized=grounded,
    )
    assert "Languages (Explicit)" in base_model.skills_categorized
    assert "Frameworks (Contextual)" in base_model.skills_categorized


def test_contextual_skill_item_validation():
    """Verify ContextualSkillItem schema validation and error constraints."""
    # Valid item
    item = ContextualSkillItem(
        skill="Docker",
        evidence="Containerized microservices with Docker multi-stage builds",
    )
    assert item.skill == "Docker"
    assert "Containerized" in item.evidence

    # Reject empty skill
    with pytest.raises(ValidationError):
        ContextualSkillItem(skill="", evidence="Valid evidence excerpt from resume")

    # Reject too short evidence
    with pytest.raises(ValidationError):
        ContextualSkillItem(skill="Docker", evidence="Doc")


def test_orchestrator_integration_with_grounding(db_session):
    """
    Verify full orchestrator flow with skill grounding:
    1. Unsupported skills in Gemini output are dropped.
    2. Verified explicit and contextual skills are retained.
    3. Empty categories are dropped.
    4. Rejected skills are NOT added to missing_or_uncertain_elements.
    """
    candidate = Candidate(
        full_name="Bob Engineer",
        email="bob_grounding_test@example.com",
        candidate_type=CandidateType.experienced,
    )
    db_session.add(candidate)
    db_session.commit()

    resume_text = (
        "Bob Engineer\nbob@example.com\n"
        "EXPERIENCE\n"
        "Senior Developer | TechFlow | 2021 - Present\n"
        "• Built backend REST APIs using Python and FastAPI, improving throughput by 40%.\n"
        "• Deployed containerized applications with Docker onto cloud infrastructure.\n"
        "SKILLS\n"
        "Languages: Python, SQL\n"
        "Frameworks: FastAPI\n"
        "Tools: Docker, Git"
    )

    resume = Resume(
        candidate_id=candidate.id,
        original_filename="bob_resume.pdf",
        file_path="/tmp/bob_resume.pdf",
        file_type="pdf",
        upload_status=UploadStatus.completed,
        extracted_text=resume_text,
    )
    db_session.add(resume)
    db_session.commit()

    # Gemini output contains real skills + hallucinated/unsupported skills
    mock_gemini = GeminiAnalysisOutput(
        summary="Experienced senior developer with backend and cloud foundations.",
        skills_categorized=SkillCategorizationSchema(
            explicit={
                "Languages": ["Python", "SQL", "Rust", "Kotlin"],  # Rust, Kotlin unsupported!
                "Frameworks": ["FastAPI"],
                "HallucinatedCategory": ["GraphQL", "Kafka"],  # Entire category unsupported!
            },
            contextual={
                "Infrastructure": [
                    ContextualSkillItem(
                        skill="Docker",
                        evidence="Deployed containerized applications with Docker",
                    ),
                    ContextualSkillItem(
                        skill="Kubernetes",
                        evidence="Architected multi-cluster Kubernetes production",  # Fabricated!
                    ),
                ]
            },
        ),
        strengths=[
            StrengthItem(anchor="TechFlow", statement="Built high-throughput backend APIs using FastAPI."),
        ],
        improvements=[],
        suggested_roles=["Senior Backend Engineer", "Lead Developer"],
        missing_or_uncertain_elements=["Missing bachelor's graduation year"],
    )

    with patch("app.services.analysis_orchestrator.run_gemini_analysis", return_value=mock_gemini):
        analysis = orchestrate_resume_analysis(resume.id, db_session)

    # 1. Verified skills kept
    assert analysis.skills_categorized["Languages (Explicit)"] == ["Python", "SQL"]
    assert analysis.skills_categorized["Frameworks (Explicit)"] == ["FastAPI"]
    assert analysis.skills_categorized["Infrastructure (Contextual)"] == ["Docker"]

    # 2. Unsupported skills excluded
    assert "Rust" not in analysis.skills_categorized["Languages (Explicit)"]
    assert "Kotlin" not in analysis.skills_categorized["Languages (Explicit)"]
    assert "HallucinatedCategory (Explicit)" not in analysis.skills_categorized
    assert "Kubernetes" not in analysis.skills_categorized["Infrastructure (Contextual)"]

    # 3. Rejected skills must NOT be added to missing_or_uncertain_elements
    assert len(analysis.missing_or_uncertain_elements) == 1
    assert analysis.missing_or_uncertain_elements[0] == "Missing bachelor's graduation year"
    assert not any("Rust" in m for m in analysis.missing_or_uncertain_elements)
    assert not any("Kubernetes" in m for m in analysis.missing_or_uncertain_elements)

