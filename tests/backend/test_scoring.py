import pytest
from app.models.candidate import CandidateType
from app.services.scoring_engine import (
    calculate_compatibility_score,
    detect_sections,
    extract_action_verbs,
    extract_metrics,
)


STUDENT_RESUME_TEXT = """
Alex Morgan
alex.morgan@university.edu | (555) 234-5678 | github.com/alexmorgan-dev
San Francisco, CA

EDUCATION
Bachelor of Science in Computer Science
University of California, Berkeley (Expected May 2025)
Relevant Coursework: Data Structures, Algorithms, Database Systems, Computer Networks

TECHNICAL SKILLS
Languages: Python, JavaScript, C++, SQL
Frameworks: React, FastAPI, Express.js, Tailwind CSS
Tools: Git, Docker, Postman, Linux

PROJECTS
• DevPortal - Full-Stack Developer Collaboration Platform
  - Engineered an open-source collaboration tool used by 120+ active student contributors.
  - Implemented real-time messaging using WebSockets and Redis, reducing notification latency by 45%.
  - Deployed containerized microservices to AWS with automated GitHub Actions CI/CD pipeline.

• Autonomous Rover Navigation Simulation
  - Designed pathfinding algorithms using A* search in Python, improving trajectory efficiency by 18%.
  - Built interactive 2D visualization dashboard using React and Canvas API.
"""

EXPERIENCED_RESUME_TEXT = """
Sarah Jenkins
sarah.jenkins@example.com | (555) 987-6543 | linkedin.com/in/sarahjenkins-lead
Seattle, WA

PROFESSIONAL SUMMARY
Senior Software Engineer with 8+ years of experience leading cross-functional teams and designing distributed cloud architectures serving millions of users. Proven track record in microservices migrations, cloud reliability, and high-throughput systems.

PROFESSIONAL EXPERIENCE
Staff Software Engineer | CloudScale Inc. | 2021 - Present
• Spearheaded migration of legacy monolith to Kubernetes microservices, reducing AWS infrastructure costs by $180,000 annually.
• Architected high-throughput message streaming pipeline processing 45,000 requests per second with 99.99% uptime.
• Mentored 8 junior and mid-level engineers, establishing company-wide engineering best practices and code review standards.
• Automated deployment workflows across 14 global regions, decreasing release cycle times by 65%.
• Spearheaded cross-team reliability initiatives reducing incident recovery time by 40%.

Senior Backend Engineer | FinTech Innovations | 2017 - 2021
• Developed PCI-DSS compliant payment processing service processing $12M+ monthly transaction volume.
• Optimized PostgreSQL query execution plans and caching strategies, reducing p99 API latency by 72ms.
• Managed disaster recovery protocols, achieving zero data loss during simulated failovers.
• Implemented automated integration test suites increasing codebase test coverage from 62% to 91%.

TECHNICAL SKILLS
Languages: Go, Python, TypeScript, Java, SQL
Infrastructure & Cloud: AWS, Kubernetes, Terraform, Docker, Kafka, CI/CD
Databases: PostgreSQL, Redis, Elasticsearch, DynamoDB

EDUCATION
Bachelor of Science in Computer Science, University of Washington (2017)
"""

MINIMAL_TEXT = """
John Doe
Seeking a job as developer.
I know Python and HTML.
"""


def test_detect_sections():
    sections = detect_sections(STUDENT_RESUME_TEXT)
    assert "Education" in sections
    assert "Skills" in sections
    assert "Projects" in sections

    exp_sections = detect_sections(EXPERIENCED_RESUME_TEXT)
    assert "Summary" in exp_sections
    assert "Experience" in exp_sections
    assert "Skills" in exp_sections
    assert "Education" in exp_sections


def test_extract_verbs_and_metrics():
    verb_count, verbs = extract_action_verbs(STUDENT_RESUME_TEXT)
    assert verb_count >= 4
    assert "engineered" in verbs or "implemented" in verbs or "deployed" in verbs

    metric_count, metrics = extract_metrics(STUDENT_RESUME_TEXT)
    assert metric_count >= 2  # 120+, 45%, 18%


def test_student_scoring_lenient_on_metrics():
    """Verify student profile is evaluated based on education and projects with metric leniency."""
    result = calculate_compatibility_score(STUDENT_RESUME_TEXT, CandidateType.student)

    assert result.compatibility_score >= 80
    assert result.section_score >= 80
    assert result.impact_score >= 70
    assert result.formatting_score >= 80
    assert result.has_email is True
    assert result.has_phone is True
    assert result.has_links is True

    # Breakdown verification
    breakdown = result.scoring_breakdown
    assert breakdown["candidate_type"] == "student"
    assert "section_factors" in breakdown
    assert "impact_factors" in breakdown
    assert "formatting_factors" in breakdown


def test_experienced_scoring_requires_high_metrics():
    """Verify experienced scoring evaluates leadership, scale, and high metrics."""
    result = calculate_compatibility_score(EXPERIENCED_RESUME_TEXT, CandidateType.experienced)

    assert result.compatibility_score >= 85
    assert result.section_score >= 90
    assert result.impact_score >= 85
    assert result.formatting_score >= 85
    assert result.detected_metrics_count >= 4
    assert result.detected_verbs_count >= 6


def test_context_aware_metric_penalties():
    """
    Verify that an identical resume with zero metrics receives a far milder penalty
    for a student than for an experienced candidate.
    """
    no_metric_resume = """
    Jane Doe
    jane.doe@example.com | (555) 123-4567 | github.com/janedoe
    
    EDUCATION
    BS in Computer Science, Tech University
    
    TECHNICAL SKILLS
    Python, Java, React, SQL, Git
    
    PROJECTS
    • Web Application
      - Developed user authentication and dashboard using React.
      - Built REST API endpoints with FastAPI and SQLite.
      - Deployed application to cloud hosting.
    """

    student_res = calculate_compatibility_score(no_metric_resume, CandidateType.student)
    experienced_res = calculate_compatibility_score(no_metric_resume, CandidateType.experienced)

    # Student should score significantly higher than experienced on this entry-level text
    assert student_res.compatibility_score > experienced_res.compatibility_score
    # Impact score for student should be more forgiving
    assert student_res.impact_score > experienced_res.impact_score


def test_empty_and_whitespace_text():
    res_empty = calculate_compatibility_score("", CandidateType.student)
    assert res_empty.compatibility_score == 0
    assert res_empty.section_score == 0
    assert res_empty.impact_score == 0
    assert res_empty.formatting_score == 0
    assert res_empty.identified_sections == []

    res_spaces = calculate_compatibility_score("    \n\n  ", CandidateType.fresher)
    assert res_spaces.compatibility_score == 0


def test_minimal_resume():
    res = calculate_compatibility_score(MINIMAL_TEXT, CandidateType.fresher)
    # Score should be low due to missing sections, low word count, missing links/phone
    assert res.compatibility_score < 50
    assert res.has_email is False
    assert res.has_phone is False
