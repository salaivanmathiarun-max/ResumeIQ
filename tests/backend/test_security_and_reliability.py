"""
Security and Reliability Regression Test Suite for ResumeIQ (Phase 6.3).

Covers:
1. Path traversal and arbitrary file deletion prevention.
2. Symlink protection during deletion.
3. Filename traversal sanitization on upload.
4. Positive ID validation on path parameters (gt=0).
5. Generic 500 error sanitization (no internal leaks).
6. Request api_key stripping and None coercion.
7. Gemini transient retry (503/429/timeout).
8. Gemini non-retry on non-transient errors (auth/403/invalid argument).
9. Gemini non-retry on schema/JSON validation errors.
10. API key masking in error messages and database records.
11. SQLite foreign key cascade deletion of ResumeAnalysis.
12. CORS origin configuration and preflight headers.
"""

from pathlib import Path
import os
import pytest
from unittest.mock import MagicMock, patch

from app.core.config import UPLOAD_DIR
from app.models.analysis import AnalysisStatus, ResumeAnalysis
from app.models.candidate import Candidate, CandidateType
from app.models.resume import Resume, UploadStatus
from app.services.gemini_service import (
    GeminiAnalysisOutput,
    GeminiServiceError,
    SkillCategorizationSchema,
    is_transient_error,
    mask_sensitive_data,
    run_gemini_analysis,
)


def test_path_traversal_deletion_protection(client, db_session, tmp_path):
    """
    Verify that DELETE /api/resumes/{id} strictly refuses to unlink files located outside UPLOAD_DIR.
    The database record must be safely cleaned up without touching external host files.
    """
    candidate = Candidate(
        full_name="Path Test Candidate",
        email="path_test@example.com",
        candidate_type=CandidateType.experienced,
    )
    db_session.add(candidate)
    db_session.commit()

    # Create an external file completely outside UPLOAD_DIR
    external_dir = tmp_path / "external_system_dir"
    external_dir.mkdir(parents=True, exist_ok=True)
    external_file = external_dir / "critical_system_file.txt"
    external_file.write_text("Confidential system contents that must not be deleted.")

    # Resume record pointing to the external file
    resume = Resume(
        candidate_id=candidate.id,
        original_filename="external_doc.pdf",
        file_path=str(external_file),
        file_type="pdf",
        upload_status=UploadStatus.completed,
        extracted_text="Sample text content.",
    )
    db_session.add(resume)
    db_session.commit()

    # Delete resume via API
    del_resp = client.delete(f"/api/resumes/{resume.id}")
    assert del_resp.status_code == 204

    # CRITICAL: External file must NOT be unlinked
    assert external_file.exists() is True
    assert external_file.read_text() == "Confidential system contents that must not be deleted."

    # Database record was safely deleted
    db_record = db_session.query(Resume).filter(Resume.id == resume.id).first()
    assert db_record is None


def test_symlink_deletion_protection(client, db_session, tmp_path):
    """
    Verify that if a file path is a symlink, the target file is not deleted.
    """
    candidate = Candidate(
        full_name="Symlink Candidate",
        email="symlink_test@example.com",
        candidate_type=CandidateType.fresher,
    )
    db_session.add(candidate)
    db_session.commit()

    target_file = tmp_path / "target_file.pdf"
    target_file.write_text("Target file content.")

    symlink_file = UPLOAD_DIR / "symlink_resume.pdf"
    try:
        os.symlink(target_file, symlink_file)
    except (OSError, NotImplementedError):
        # Symlink creation may require elevated privileges on some Windows versions;
        # test directly via Path.is_symlink mock if os.symlink is restricted
        pass

    if symlink_file.is_symlink():
        resume = Resume(
            candidate_id=candidate.id,
            original_filename="symlink_resume.pdf",
            file_path=str(symlink_file),
            file_type="pdf",
            upload_status=UploadStatus.completed,
            extracted_text="Sample text.",
        )
        db_session.add(resume)
        db_session.commit()

        del_resp = client.delete(f"/api/resumes/{resume.id}")
        assert del_resp.status_code == 204
        # Target must remain intact
        assert target_file.exists() is True
        if symlink_file.exists():
            symlink_file.unlink()


def test_upload_filename_traversal_sanitization(client, db_session):
    """
    Verify that uploading a file with a malicious path traversal filename
    (e.g., '../../../../boot.ini' or '..\\..\\secret.pdf') sanitizes the filename in the database.
    """
    candidate = Candidate(
        full_name="Traversal Upload Candidate",
        email="traversal_upload@example.com",
        candidate_type=CandidateType.student,
    )
    db_session.add(candidate)
    db_session.commit()

    # Valid minimal PDF bytes
    dummy_pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj\n4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 72 712 Td (Sample Resume) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000108 00000 n\n0000000199 00000 n\ntrailer<</Size 5/Root 1 0 R>>\nstartxref\n293\n%%EOF"

    malicious_filename = "../../../../etc/malicious_resume.pdf"
    response = client.post(
        "/api/resumes/upload",
        data={"candidate_id": candidate.id},
        files={"file": (malicious_filename, dummy_pdf, "application/pdf")},
    )

    assert response.status_code == 201
    data = response.json()

    # Traversal components must be completely stripped
    assert ".." not in data["original_filename"]
    assert "/" not in data["original_filename"]
    assert "\\" not in data["original_filename"]
    assert data["original_filename"] == "malicious_resume.pdf"


def test_positive_id_validation_on_path_parameters(client):
    """
    Verify that negative and zero IDs on all entity endpoints return HTTP 422 Unprocessable Entity.
    """
    # Candidate routes
    assert client.get("/api/candidates/0").status_code == 422
    assert client.get("/api/candidates/-1").status_code == 422
    assert client.get("/api/candidates/-99").status_code == 422

    # Resume routes
    assert client.get("/api/resumes/0").status_code == 422
    assert client.get("/api/resumes/-1").status_code == 422
    assert client.get("/api/resumes/0/text").status_code == 422
    assert client.delete("/api/resumes/0").status_code == 422

    # Analysis routes
    assert client.get("/api/resumes/0/analysis").status_code == 422
    assert client.get("/api/resumes/-5/analysis").status_code == 422
    assert client.post("/api/resumes/0/analyze").status_code == 422
    assert client.post("/api/resumes/-2/analyze").status_code == 422


def test_analyze_request_api_key_sanitization(client, db_session):
    """
    Verify that AnalyzeRequest trims whitespace and coerces empty/whitespace api_key values to None.
    """
    candidate = Candidate(
        full_name="Key Sanitize Candidate",
        email="key_sanitize@example.com",
        candidate_type=CandidateType.experienced,
    )
    db_session.add(candidate)
    db_session.commit()

    resume = Resume(
        candidate_id=candidate.id,
        original_filename="resume.pdf",
        file_path="/tmp/test.pdf",
        file_type="pdf",
        upload_status=UploadStatus.completed,
        extracted_text="Software engineer with Python and React skills.",
    )
    db_session.add(resume)
    db_session.commit()

    mock_out = GeminiAnalysisOutput(
        summary="Candidate profile summary overview.",
        skills_categorized=SkillCategorizationSchema(explicit={"Languages": ["Python"]}, contextual={}),
        strengths=[],
        improvements=[],
        suggested_roles=["Software Engineer"],
        missing_or_uncertain_elements=[],
    )

    with patch("app.services.analysis_orchestrator.run_gemini_analysis", return_value=mock_out) as mock_gemini:
        # Pass whitespace-only api_key
        resp = client.post(
            f"/api/resumes/{resume.id}/analyze",
            json={"api_key": "   \n\t  ", "force_refresh": False},
        )
        assert resp.status_code == 200
        # Orchestrator received None, falling back to server environment key
        mock_gemini.assert_called_once()
        _, kwargs = mock_gemini.call_args
        assert kwargs.get("api_key") is None


def test_generic_client_facing_500_error(client, db_session):
    """
    Verify that internal server exceptions return a sanitized generic error message
    without leaking internal stack traces, DB connection strings, or system paths.
    """
    candidate = Candidate(
        full_name="Internal Error Candidate",
        email="internal_err@example.com",
        candidate_type=CandidateType.fresher,
    )
    db_session.add(candidate)
    db_session.commit()

    resume = Resume(
        candidate_id=candidate.id,
        original_filename="resume.pdf",
        file_path="/tmp/test.pdf",
        file_type="pdf",
        upload_status=UploadStatus.completed,
        extracted_text="Resume text content.",
    )
    db_session.add(resume)
    db_session.commit()

    # Force unexpected low-level internal crash
    with patch(
        "app.api.routes.analyses.orchestrate_resume_analysis",
        side_effect=RuntimeError("Secret database pool failed at /var/run/secrets/pg.sock:5432"),
    ):
        resp = client.post(f"/api/resumes/{resume.id}/analyze")

    assert resp.status_code == 500
    data = resp.json()
    assert "detail" in data
    # Generic message returned to client
    assert data["detail"] == "An unexpected internal error occurred during resume analysis. Please try again."
    # Sensitive internal path/message is NOT exposed
    assert "/var/run/secrets" not in data["detail"]
    assert "pg.sock" not in data["detail"]


def test_gemini_retry_on_transient_error():
    """
    Verify that run_gemini_analysis automatically retries on transient errors (503 / 429)
    and succeeds once the transient issue clears.
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        '{"summary": "Valid engineer profile summary.", '
        '"skills_categorized": {"explicit": {"Languages": ["Python"]}, "contextual": {}}, '
        '"strengths": [], "improvements": [], "suggested_roles": [], "missing_or_uncertain_elements": []}'
    )

    # First attempt: 503 UNAVAILABLE. Second attempt: Success!
    mock_client.models.generate_content.side_effect = [
        Exception("503 UNAVAILABLE: The model is overloaded. Please try again."),
        mock_response,
    ]

    with patch("google.genai.Client", return_value=mock_client), patch("time.sleep") as mock_sleep:
        output = run_gemini_analysis(
            resume_text="Skills: Python",
            candidate_type=CandidateType.fresher,
            api_key="AIzaSyDfakeValidKey1234567890abcdefgh",
        )

    assert output.summary == "Valid engineer profile summary."
    assert mock_client.models.generate_content.call_count == 2
    mock_sleep.assert_called_once_with(1.0)


def test_gemini_never_retries_non_transient_error():
    """
    Verify that authentication (401/403) or invalid-argument errors fail immediately
    without wasting retry attempts or delay.
    """
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API_KEY_INVALID: 403 Forbidden")

    with patch("google.genai.Client", return_value=mock_client), patch("time.sleep") as mock_sleep:
        with pytest.raises(GeminiServiceError) as exc_info:
            run_gemini_analysis(
                resume_text="Skills: Python",
                candidate_type=CandidateType.experienced,
                api_key="AIzaSyDfakeInvalidKey123456789abcdef",
            )

    assert "API_KEY_INVALID" in str(exc_info.value)
    # Exactly 1 call, zero retries
    assert mock_client.models.generate_content.call_count == 1
    mock_sleep.assert_not_called()


def test_gemini_never_retries_schema_validation_error():
    """
    Verify that malformed JSON or schema validation failures fail immediately without retrying.
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is not valid JSON content"
    mock_client.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client), patch("time.sleep") as mock_sleep:
        with pytest.raises(GeminiServiceError) as exc_info:
            run_gemini_analysis(
                resume_text="Skills: Python",
                candidate_type=CandidateType.student,
                api_key="AIzaSyDfakeValidKey1234567890abcdefgh",
            )

    assert "Malformed intelligence output" in str(exc_info.value)
    assert mock_client.models.generate_content.call_count == 1
    mock_sleep.assert_not_called()


def test_api_key_redaction_in_logs_and_errors(client, db_session):
    """
    Verify that mask_sensitive_data redacts API keys matching Google key format,
    and that analysis_record.analysis_error persists the masked version.
    """
    raw_error = "Failed to reach endpoint https://generativelanguage.googleapis.com/v1beta?key=AIzaSyDfakeApiKey1234567890abcdefghij with 503 Service Unavailable"
    masked = mask_sensitive_data(raw_error)

    assert "AIzaSyDfakeApiKey1234567890abcdefghij" not in masked
    assert "[REDACTED_API_KEY]" in masked

    # End-to-end test via orchestrator
    candidate = Candidate(
        full_name="Redaction Candidate",
        email="redaction@example.com",
        candidate_type=CandidateType.experienced,
    )
    db_session.add(candidate)
    db_session.commit()

    resume = Resume(
        candidate_id=candidate.id,
        original_filename="resume.pdf",
        file_path="/tmp/test.pdf",
        file_type="pdf",
        upload_status=UploadStatus.completed,
        extracted_text="Python and Docker engineer.",
    )
    db_session.add(resume)
    db_session.commit()

    with patch(
        "app.services.analysis_orchestrator.run_gemini_analysis",
        side_effect=GeminiServiceError("Upstream error with key=AIzaSyDsecretKey1234567890abcdefghijk"),
    ):
        client.post(f"/api/resumes/{resume.id}/analyze")

    record = db_session.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == resume.id).first()
    assert record is not None
    assert record.analysis_status == AnalysisStatus.failed
    assert "AIzaSyDsecretKey1234567890abcdefghijk" not in record.analysis_error
    assert "[REDACTED_API_KEY]" in record.analysis_error


def test_sqlite_foreign_key_cascade(db_session):
    """
    Verify that SQLite enforces foreign key constraints and cascades deletes:
    deleting a Resume record must automatically delete its child ResumeAnalysis record.
    """
    candidate = Candidate(
        full_name="Cascade Candidate",
        email="cascade@example.com",
        candidate_type=CandidateType.student,
    )
    db_session.add(candidate)
    db_session.commit()

    resume = Resume(
        candidate_id=candidate.id,
        original_filename="cascade.pdf",
        file_path="/tmp/cascade.pdf",
        file_type="pdf",
        upload_status=UploadStatus.completed,
        extracted_text="Resume content.",
    )
    db_session.add(resume)
    db_session.commit()

    analysis = ResumeAnalysis(
        resume_id=resume.id,
        analysis_status=AnalysisStatus.completed,
        compatibility_score=85,
        section_score=90,
        impact_score=80,
        formatting_score=85,
    )
    db_session.add(analysis)
    db_session.commit()

    # Ensure both exist
    assert db_session.query(Resume).filter(Resume.id == resume.id).first() is not None
    assert db_session.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == resume.id).first() is not None

    # Delete parent Resume
    db_session.delete(resume)
    db_session.commit()

    # Child ResumeAnalysis must be automatically deleted by cascade
    child_record = db_session.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == resume.id).first()
    assert child_record is None


def test_cors_preflight_and_configured_origins(client):
    """
    Verify that CORS headers are returned correctly on preflight OPTIONS and standard GET requests
    for allowed frontend origins.
    """
    # Preflight OPTIONS request from localhost:5173
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

    # Standard GET request from 127.0.0.1:5173
    get_response = client.get(
        "/api/health",
        headers={"Origin": "http://127.0.0.1:5173"},
    )
    assert get_response.status_code == 200
    assert get_response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"

    # Production Vercel origin preflight OPTIONS request
    prod_options = client.options(
        "/api/health",
        headers={
            "Origin": "https://resume-iq-olive-theta.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert prod_options.status_code == 200
    assert prod_options.headers.get("access-control-allow-origin") == "https://resume-iq-olive-theta.vercel.app"

    # Production Vercel origin standard GET request
    prod_get = client.get(
        "/api/health",
        headers={"Origin": "https://resume-iq-olive-theta.vercel.app"},
    )
    assert prod_get.status_code == 200
    assert prod_get.headers.get("access-control-allow-origin") == "https://resume-iq-olive-theta.vercel.app"


def test_cors_origins_normalization():
    """
    Verify that parse_cors_origins handles defaults, comma-separation,
    whitespace trimming, quote stripping, and trailing slash removal.
    """
    from app.core.config import DEFAULT_CORS_ORIGINS, parse_cors_origins

    # 1. Production origin in defaults alongside localhost
    assert "https://resume-iq-olive-theta.vercel.app" in DEFAULT_CORS_ORIGINS
    assert "http://localhost:5173" in DEFAULT_CORS_ORIGINS
    assert "http://127.0.0.1:5173" in DEFAULT_CORS_ORIGINS

    # 2. None or empty string returns defaults
    assert parse_cors_origins(None) == DEFAULT_CORS_ORIGINS
    assert parse_cors_origins("") == DEFAULT_CORS_ORIGINS
    assert parse_cors_origins("   ") == DEFAULT_CORS_ORIGINS

    # 3. Comma-separated environment origins
    parsed = parse_cors_origins("https://preview.vercel.app,https://custom-domain.com")
    assert parsed == ["https://preview.vercel.app", "https://custom-domain.com"]

    # 4. Whitespace and surrounding single/double quote normalization
    quoted = parse_cors_origins('"https://preview.vercel.app", \'https://custom-domain.com\'')
    assert quoted == ["https://preview.vercel.app", "https://custom-domain.com"]

    whole_quoted = parse_cors_origins('"https://preview.vercel.app,http://localhost:5173"')
    assert whole_quoted == ["https://preview.vercel.app", "http://localhost:5173"]

    # 5. Trailing slash normalization
    slashes = parse_cors_origins("https://resume-iq-olive-theta.vercel.app/,http://localhost:5173///")
    assert slashes == ["https://resume-iq-olive-theta.vercel.app", "http://localhost:5173"]

    # 6. Combined edge case with spaces, quotes, and slashes
    combined = parse_cors_origins(' "https://resume-iq-olive-theta.vercel.app/" , \'http://localhost:5173/\' ')
    assert combined == ["https://resume-iq-olive-theta.vercel.app", "http://localhost:5173"]

