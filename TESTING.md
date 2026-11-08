# ResumeIQ — Testing Documentation

This document describes the testing architecture, test suites, execution commands, and verification processes for **ResumeIQ**.

---

## 1. Testing Architecture & Design Philosophy

The ResumeIQ test suite is engineered for zero side effects, complete determinism, and rapid execution:

1. **In-Memory Database Isolation**:
   - Tests execute against an isolated SQLite database (`sqlite:///:memory:`).
   - The production database (`backend/resumeiq.db`) is never modified or accessed during automated testing.
   - Database tables are dropped and recreated cleanly for every test function via pytest fixtures.
2. **Zero Live AI Dependencies (Mocked Gemini)**:
   - External calls to the Google Gemini API are strictly mocked via `unittest.mock.patch`.
   - No network egress is initiated during test execution, ensuring zero token consumption, immune to rate limits or API quotas.
3. **Isolated Test File Storage**:
   - File upload tests operate in temporary directory fixtures (`tmp_path`) cleaned up automatically after execution.
   - The production upload directory (`data/uploads`) remains completely untouched.
4. **Fast Execution**:
   - The entire 75-test backend suite runs in under 4 seconds.

---

## 2. Test Suite Breakdown (75 Tests across 10 Modules)

The backend test suite is organized into 10 modules under `tests/backend/`:

```
tests/backend/
├── test_analysis_edge_cases.py          # 12 tests: candidate fairness, stress tests, edge cases
├── test_analysis_routes.py              #  5 tests: analysis endpoints, error handling, retries
├── test_candidate.py                    #  5 tests: candidate CRUD, duplicate emails, validation
├── test_gemini_schemas.py               #  6 tests: Pydantic schemas, validation, structured output
├── test_health.py                       #  2 tests: / and /api/health endpoint probes
├── test_resume.py                       #  3 tests: resume metadata CRUD, foreign key constraints
├── test_resume_upload.py                # 11 tests: PDF/DOCX ingestion, MIME checks, oversized files
├── test_scoring.py                      #  7 tests: deterministic scoring algorithm, verb & metric counting
├── test_security_and_reliability.py     # 12 tests: path traversal, API keys, retries, cascades, CORS
└── test_skill_grounding.py              # 12 tests: explicit and contextual evidence grounding
```

---

### 2.1 Module Details

#### 1. `test_security_and_reliability.py` (12 tests)
Verifies Phase 6.3 security hardening and defensive engineering:
- `test_path_traversal_deletion_protection`: Ensures deletion rejects paths outside `UPLOAD_DIR`.
- `test_symlink_deletion_protection`: Verifies symlinks targeting external files are never unlinked.
- `test_upload_filename_traversal_sanitization`: Verifies `../` in filenames is stripped.
- `test_positive_id_validation_on_path_parameters`: Validates `candidate_id` and `resume_id` reject `0`, `-1`.
- `test_analyze_request_api_key_sanitization`: Verifies API keys are trimmed and whitespace treated as `None`.
- `test_generic_client_facing_500_error`: Ensures unhandled server exceptions return generic error responses.
- `test_gemini_retry_on_transient_error`: Confirms HTTP 429/503 errors trigger bounded exponential retries.
- `test_gemini_never_retries_non_transient_error`: Confirms 400/401/403/404 errors fail immediately without retry.
- `test_gemini_never_retries_schema_validation_error`: Ensures malformed structured outputs are not retried.
- `test_api_key_redaction_in_logs_and_errors`: Verifies `AIza...` keys are redacted from logs and errors.
- `test_sqlite_foreign_key_cascade`: Tests SQLite `PRAGMA foreign_keys=ON` cascade deletions.
- `test_cors_preflight_and_configured_origins`: Confirms allowed origins receive CORS headers and unauthorized origins are rejected.

#### 2. `test_analysis_edge_cases.py` (12 tests)
Covers Phase 6.2.4 edge cases, candidate fairness, and robustness:
- `test_empty_gemini_output_database_and_api_roundtrip`: Empty AI responses persist and deserialize cleanly.
- `test_preserve_deterministic_scores_when_gemini_fails`: Confirms scoring persists even if AI fails.
- `test_sequential_analysis_retry_idempotency`: Re-running analysis updates or replaces the single record.
- `test_legacy_database_record_deserialization_compatibility`: Legacy records with nulls deserialize without error.
- `test_candidate_tier_scoring_fairness`: Evaluates student, fresher, and experienced scoring rules.
- `test_candidate_specific_prompt_calibration`: Verifies prompt changes according to candidate type.
- `test_missing_sections_and_single_section_resumes`: Evaluates resumes missing standard sections.
- `test_multiline_contextual_evidence_normalization`: Handles multiline evidence quotes with whitespace.
- `test_large_resume_stress_test_5000_words`: Benchmark test processing a 5,000-word resume.
- `test_unicode_smart_quotes_non_breaking_spaces_and_bullets`: Normalization of non-ASCII characters.
- `test_two_column_scrambled_extraction_text`: Handles scrambled text from multi-column PDFs.
- `test_versioned_and_numeric_skills`: Grounding of versioned skills (Python 3.12, Angular 17, C++20, HTML5).

#### 3. `test_skill_grounding.py` (12 tests)
Covers Phase 6.2.3 evidence-based skill grounding:
- `test_explicit_direct_matches`: Direct exact matches in extracted text.
- `test_alias_matches_and_non_matches`: Alias dictionary mapping (e.g., TS -> TypeScript, K8s -> Kubernetes).
- `test_short_and_ambiguous_skill_safeguards`: Word-boundary matching for short acronyms (e.g., C, R, Go).
- `test_valid_contextual_evidence`: Contextual skills with verbatim quotes in the resume text.
- `test_fabricated_evidence_rejection`: Discards skills where quoted evidence cannot be found in resume text.
- `test_existing_evidence_without_substantive_support_rejected`: Rejects empty or non-substantive evidence.
- `test_empty_category_removal`: Cleans empty categories after grounding filter.
- `test_mixed_supported_and_unsupported_skills`: Keeps verified skills and removes hallucinated skills.
- `test_deduplication_preserving_order`: Deduplicates skills across categories while preserving order.
- `test_existing_api_contract_compatibility`: Preserves dictionary format returned to client.
- `test_contextual_skill_item_validation`: Pydantic schema validation of `ContextualSkillItem`.
- `test_orchestrator_integration_with_grounding`: Full orchestrator grounding integration test.

#### 4. `test_resume_upload.py` (11 tests)
Validates document ingestion, format verification, and text extraction:
- `test_upload_pdf_success`: Uploads real PDF binary, verifies PyMuPDF extraction and DB record.
- `test_upload_docx_success`: Uploads real DOCX binary, verifies python-docx extraction.
- `test_upload_unsupported_extension`: Rejects `.txt`, `.jpg`, `.png`, etc.
- `test_upload_mismatched_content_fake_pdf`: Rejects non-PDF binary named `.pdf`.
- `test_upload_mismatched_content_fake_docx`: Rejects non-DOCX binary named `.docx`.
- `test_upload_empty_file`: Rejects 0-byte uploaded files.
- `test_upload_pdf_without_readable_text`: Rejects scanned image PDFs without selectable text.
- `test_upload_oversized_file`: Rejects files exceeding `MAX_FILE_SIZE_BYTES` (5 MB).
- `test_upload_nonexistent_candidate`: Rejects upload referencing an invalid candidate ID.
- `test_get_nonexistent_resume_text`: Returns 404 for missing resume text preview.
- `test_normalize_text_utility`: Tests character normalization utility.

#### 5. `test_scoring.py` (7 tests)
Tests the deterministic scoring engine:
- `test_detect_sections`: Section header recognition across standard variants.
- `test_extract_verbs_and_metrics`: Regex detection of strong action verbs and metrics.
- `test_student_scoring_lenient_on_metrics`: Verifies students are not penalized for low metric density.
- `test_experienced_scoring_requires_high_metrics`: Verifies experienced candidates require quantifiable metrics.
- `test_context_aware_metric_penalties`: Level-aware scoring calibrations.
- `test_empty_and_whitespace_text`: Safe handling of empty or blank resume text.
- `test_minimal_resume`: Correct baseline evaluation of minimal resumes.

#### 6. `test_gemini_schemas.py` (6 tests)
Tests Pydantic v2 schemas and validation for Gemini interactions:
- `test_strength_item_validation_and_display`: Validates strength item constraints.
- `test_strength_item_rejection_of_empty_strings`: Enforces non-empty strings.
- `test_skill_categorization_schema_structure`: Explicit vs contextual schema structure.
- `test_gemini_analysis_output_allows_empty_lists`: Verifies fallback handling when lists are empty.
- `test_gemini_analysis_output_rejection_of_too_short_summary`: Enforces minimum summary length.
- `test_orchestrator_formats_structured_strengths_and_skills`: Validates orchestrator data mapping.

#### 7. `test_analysis_routes.py` (5 tests)
Tests HTTP endpoints under `/api/resumes/{id}/analyze` and `/analysis`:
- `test_analyze_resume_success`: Full mocked analysis pipeline roundtrip.
- `test_get_resume_analysis`: Retrieval of existing analysis record.
- `test_get_nonexistent_analysis`: 404 for un-analyzed resume.
- `test_analyze_resume_without_extracted_text`: 400 when resume has no text.
- `test_analyze_gemini_failure_and_safe_retry`: Confirms score preservation when AI fails.

#### 8. `test_candidate.py` (5 tests)
Tests candidate CRUD endpoints:
- `test_create_and_get_candidate`: Candidate creation and retrieval.
- `test_list_candidates`: Listing all candidates.
- `test_create_candidate_duplicate_email`: Rejection of duplicate email with 400.
- `test_get_nonexistent_candidate`: 404 for invalid candidate ID.
- `test_create_candidate_invalid_payload`: 422 for malformed email or missing fields.

#### 9. `test_resume.py` (3 tests)
Tests resume metadata management:
- `test_resume_crud_lifecycle`: Metadata creation, retrieval, and deletion.
- `test_create_resume_nonexistent_candidate`: Rejection when candidate does not exist.
- `test_get_and_delete_nonexistent_resume`: 404 handling.

#### 10. `test_health.py` (2 tests)
Tests root and health probes:
- `test_health_endpoint`: `GET /api/health` returns `{"status": "ok"}`.
- `test_root_endpoint`: `GET /` returns API status and docs URL.

---

## 3. Test Execution Instructions

### 3.1 Prerequisites
Ensure the virtual environment is activated:
```powershell
# Windows PowerShell
.\backend\.venv\Scripts\Activate.ps1
```

### 3.2 Running the Full Backend Test Suite
```powershell
# Run all 75 tests with summary
backend\.venv\Scripts\pytest tests\backend -v
```

### 3.3 Running Specific Test Modules
```powershell
# Run only security and reliability tests
backend\.venv\Scripts\pytest tests\backend\test_security_and_reliability.py -v

# Run only skill grounding tests
backend\.venv\Scripts\pytest tests\backend\test_skill_grounding.py -v

# Run only analysis edge case tests
backend\.venv\Scripts\pytest tests\backend\test_analysis_edge_cases.py -v
```

### 3.4 Running Frontend Production Build Verification
Verify the React 18 production build compiles cleanly without syntax or typing issues:
```powershell
cd frontend
npm run build
cd ..
```

---

## 4. Test Assumptions & Known Boundaries

1. **OCR Limitations**:
   - The test suite explicitly confirms that image-only / non-selectable text PDFs are rejected with `DocumentProcessingError` (`400 Bad Request`). Optical Character Recognition (OCR) is outside the current scope of the PyMuPDF text stream extractor.
2. **Deterministic Diagnostic Benchmarks**:
   - The 5,000-word stress test is designed as a diagnostic benchmark to ensure parser and regex stability under high load; it does not impose hard machine-dependent timing constraints.
3. **Mocked Gemini Testing**:
   - End-to-end AI tests simulate Gemini API responses (including simulated HTTP 429 and 503 retry scenarios) to maintain 100% offline determinism and eliminate cloud quota dependencies.

