# ResumeIQ — API Documentation

This reference document details all REST endpoints provided by the **ResumeIQ** backend service.

---

## 1. Overview & Conventions

### 1.1 Base URL & Interactive Docs
- **Base URL**: `http://localhost:8000` (or `http://127.0.0.1:8000`)
- **API Prefix**: `/api` (for domain resources)
- **Interactive OpenAPI Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative API Reference**: `http://localhost:8000/redoc` (ReDoc)

### 1.2 Headers & Content Types
- Standard JSON endpoints require:
  ```http
  Content-Type: application/json
  Accept: application/json
  ```
- File upload endpoint (`POST /api/resumes/upload`) requires:
  ```http
  Content-Type: multipart/form-data
  ```

### 1.3 Path Validation & Error Format
- All resource ID path parameters (`candidate_id`, `resume_id`) enforce strict positive integer constraints (`gt=0`).
- Non-positive integer identifiers (e.g., `0`, `-1`) reject immediately with `422 Unprocessable Entity`.
- Standard API error responses adhere to FastAPI's JSON schema:
  ```json
  {
    "detail": "Error description message"
  }
  ```
- Unhandled internal server errors return generic `500 Internal Server Error` details to protect internal infrastructure details.

---

## 2. Endpoint Index (13 Endpoints)

| # | Method | Path | Summary | Success Code |
|---|---|---|---|---|
| 1 | `GET` | `/` | Root service ping and docs link | `200 OK` |
| 2 | `GET` | `/api/health` | Service health status check | `200 OK` |
| 3 | `POST` | `/api/candidates/` | Register a new candidate profile | `201 Created` |
| 4 | `GET` | `/api/candidates/` | List all registered candidates | `200 OK` |
| 5 | `GET` | `/api/candidates/{candidate_id}` | Retrieve candidate by ID | `200 OK` |
| 6 | `POST` | `/api/resumes/upload` | Upload resume document (PDF/DOCX) | `201 Created` |
| 7 | `POST` | `/api/resumes/` | Create resume record directly | `200 OK` |
| 8 | `GET` | `/api/resumes/` | List all resume records | `200 OK` |
| 9 | `GET` | `/api/resumes/{resume_id}` | Retrieve resume metadata by ID | `200 OK` |
| 10 | `GET` | `/api/resumes/{resume_id}/text` | Preview extracted & normalized resume text | `200 OK` |
| 11 | `DELETE` | `/api/resumes/{resume_id}` | Delete resume and safely remove file | `204 No Content` |
| 12 | `POST` | `/api/resumes/{resume_id}/analyze` | Trigger or retry dual-engine analysis | `200 OK` |
| 13 | `GET` | `/api/resumes/{resume_id}/analysis` | Retrieve completed analysis results | `200 OK` |

---

## 3. Core & Health Endpoints

### 3.1 Root Service Ping
- **Endpoint**: `GET /`
- **Description**: Returns basic service metadata and links to OpenAPI documentation.
- **Request Parameters**: None.
- **Response**: `200 OK`
  ```json
  {
    "name": "ResumeIQ API",
    "status": "online",
    "docs_url": "/docs"
  }
  ```

---

### 3.2 Service Health Check
- **Endpoint**: `GET /api/health`
- **Description**: Simple health probe for container orchestration and uptime monitoring.
- **Request Parameters**: None.
- **Response**: `200 OK`
  ```json
  {
    "status": "ok"
  }
  ```

---

## 4. Candidate Endpoints (`/api/candidates`)

### 4.1 Create Candidate
- **Endpoint**: `POST /api/candidates/`
- **Description**: Registers a new candidate. Ensures email addresses are globally unique and valid.
- **Request Body** (`application/json`):
  | Field | Type | Required | Description |
  |---|---|---|---|
  | `full_name` | `string` | Yes | 1-255 characters |
  | `email` | `string` | Yes | Valid RFC email address |
  | `candidate_type` | `string` | Yes | Enum: `"student"`, `"fresher"`, `"experienced"` |

  *Example Request*:
  ```json
  {
    "full_name": "Jane Doe",
    "email": "jane.doe@example.com",
    "candidate_type": "experienced"
  }
  ```
- **Response**: `201 Created`
  ```json
  {
    "id": 1,
    "full_name": "Jane Doe",
    "email": "jane.doe@example.com",
    "candidate_type": "experienced",
    "created_at": "2026-11-09T00:00:00Z"
  }
  ```
- **Errors**:
  - `400 Bad Request`: Candidate with this email already exists.
  - `422 Unprocessable Entity`: Missing fields or invalid candidate type / email syntax.

---

### 4.2 List Candidates
- **Endpoint**: `GET /api/candidates/`
- **Description**: Retrieves all candidate profiles, ordered newest first.
- **Request Parameters**: None.
- **Response**: `200 OK`
  ```json
  [
    {
      "id": 1,
      "full_name": "Jane Doe",
      "email": "jane.doe@example.com",
      "candidate_type": "experienced",
      "created_at": "2026-11-09T00:00:00Z"
    }
  ]
  ```

---

### 4.3 Get Candidate by ID
- **Endpoint**: `GET /api/candidates/{candidate_id}`
- **Description**: Retrieves a single candidate profile by primary key.
- **Path Parameters**:
  | Parameter | Type | Constraint | Description |
  |---|---|---|---|
  | `candidate_id` | `integer` | `> 0` | Candidate unique identifier |
- **Response**: `200 OK`
  ```json
  {
    "id": 1,
    "full_name": "Jane Doe",
    "email": "jane.doe@example.com",
    "candidate_type": "experienced",
    "created_at": "2026-11-09T00:00:00Z"
  }
  ```
- **Errors**:
  - `404 Not Found`: Candidate ID does not exist.
  - `422 Unprocessable Entity`: `candidate_id` is non-positive or non-integer.

---

## 5. Resume Endpoints (`/api/resumes`)

### 5.1 Upload Resume Document
- **Endpoint**: `POST /api/resumes/upload`
- **Description**: Uploads a PDF or DOCX file, verifies magic bytes and extension, stores the file securely under `UPLOAD_DIR`, extracts text using PyMuPDF or python-docx, and creates a database record with status `"completed"`.
- **Request Format**: `multipart/form-data`
  | Field | Type | Required | Description |
  |---|---|---|---|
  | `candidate_id` | `integer` (Form) | Yes | Associated candidate ID (`> 0`) |
  | `file` | `UploadFile` (File) | Yes | Document file (`.pdf` or `.docx`, max 5 MB) |

- **Response**: `201 Created`
  ```json
  {
    "id": 10,
    "candidate_id": 1,
    "original_filename": "jane_doe_resume.pdf",
    "file_path": "data/uploads/1a2b3c4d_jane_doe_resume.pdf",
    "file_type": "pdf",
    "upload_status": "completed",
    "extracted_text": "Jane Doe\nSenior Software Engineer...",
    "created_at": "2026-11-09T00:00:00Z",
    "updated_at": null
  }
  ```
- **Errors**:
  - `400 Bad Request`: Unsupported extension, corrupted file structure, or empty content.
  - `404 Not Found`: Candidate ID does not exist.
  - `413 Payload Too Large`: Uploaded file exceeds 5 MB.
  - `422 Unprocessable Entity`: Non-positive `candidate_id` or missing file.

---

### 5.2 Create Resume Metadata
- **Endpoint**: `POST /api/resumes/`
- **Description**: Direct programmatic creation of a resume record without file upload.
- **Request Body** (`application/json`):
  ```json
  {
    "candidate_id": 1,
    "original_filename": "external_import.pdf",
    "file_path": "data/uploads/external_import.pdf",
    "file_type": "pdf",
    "upload_status": "completed",
    "extracted_text": "Extracted resume content here..."
  }
  ```
- **Response**: `200 OK` (returns created `ResumeRead` object).
- **Errors**:
  - `404 Not Found`: Candidate ID does not exist.
  - `422 Unprocessable Entity`: Validation failure on required fields.

---

### 5.3 List Resumes
- **Endpoint**: `GET /api/resumes/`
- **Description**: Retrieves all uploaded resume records, ordered newest first.
- **Request Parameters**: None.
- **Response**: `200 OK`
  ```json
  [
    {
      "id": 10,
      "candidate_id": 1,
      "original_filename": "jane_doe_resume.pdf",
      "file_path": "data/uploads/1a2b3c4d_jane_doe_resume.pdf",
      "file_type": "pdf",
      "upload_status": "completed",
      "extracted_text": "Jane Doe\nSenior Software Engineer...",
      "created_at": "2026-11-09T00:00:00Z",
      "updated_at": null
    }
  ]
  ```

---

### 5.4 Get Resume Metadata
- **Endpoint**: `GET /api/resumes/{resume_id}`
- **Description**: Retrieves metadata and extracted text for a specific resume record.
- **Path Parameters**:
  | Parameter | Type | Constraint | Description |
  |---|---|---|---|
  | `resume_id` | `integer` | `> 0` | Resume unique identifier |
- **Response**: `200 OK` (returns `ResumeRead` object).
- **Errors**:
  - `404 Not Found`: Resume ID not found.
  - `422 Unprocessable Entity`: `resume_id` is non-positive.

---

### 5.5 Get Resume Text Preview
- **Endpoint**: `GET /api/resumes/{resume_id}/text`
- **Description**: Returns both the raw extracted text and normalized text representation (cleaned of unicode quotes, special bullets, and formatting anomalies).
- **Path Parameters**:
  | Parameter | Type | Constraint | Description |
  |---|---|---|---|
  | `resume_id` | `integer` | `> 0` | Resume unique identifier |
- **Response**: `200 OK`
  ```json
  {
    "id": 10,
    "candidate_id": 1,
    "original_filename": "jane_doe_resume.pdf",
    "file_type": "pdf",
    "upload_status": "completed",
    "extracted_text": "Jane Doe\n• Python, FastAPI",
    "normalized_text": "Jane Doe\n- Python, FastAPI"
  }
  ```
- **Errors**:
  - `404 Not Found`: Resume ID not found.
  - `422 Unprocessable Entity`: `resume_id` is non-positive.

---

### 5.6 Delete Resume
- **Endpoint**: `DELETE /api/resumes/{resume_id}`
- **Description**: Deletes the database record, cascades deletion to child analysis records, and safely removes the stored document file on disk. Protected against path traversal: files outside `UPLOAD_DIR` and symlinks are never unlinked.
- **Path Parameters**:
  | Parameter | Type | Constraint | Description |
  |---|---|---|---|
  | `resume_id` | `integer` | `> 0` | Resume unique identifier |
- **Response**: `204 No Content` (Empty response body).
- **Errors**:
  - `404 Not Found`: Resume ID not found.
  - `422 Unprocessable Entity`: `resume_id` is non-positive.

---

## 6. Analysis Endpoints (`/api/resumes/{resume_id}/analyze` & `/analysis`)

### 6.1 Trigger Resume Analysis
- **Endpoint**: `POST /api/resumes/{resume_id}/analyze`
- **Description**: Coordinates the dual-engine analysis pipeline:
  1. Computes deterministic score (0-100) using `scoring_engine.py` calibrated to the candidate's level.
  2. Queries Google Gemini (`gemini-3.5-flash-lite`) with structured output schemas for strengths, improvement recommendations, and contextual skills.
  3. Validates and grounds skills against resume text via `skill_grounding.py`.
  4. Persists the `ResumeAnalysis` record idempotently (replaces older runs).
  5. Preserves deterministic scores and gracefully recovers if the AI service encounters transient timeouts or errors.
- **Path Parameters**:
  | Parameter | Type | Constraint | Description |
  |---|---|---|---|
  | `resume_id` | `integer` | `> 0` | Resume unique identifier |

- **Request Body** (Optional `application/json`):
  | Field | Type | Default | Description |
  |---|---|---|---|
  | `api_key` | `string` | `null` | Optional request-level Gemini API key override (sanitized and never logged) |
  | `force_refresh` | `boolean` | `false` | When true, forces a re-analysis even if a previous record exists |

  *Example Request Body*:
  ```json
  {
    "force_refresh": true
  }
  ```

- **Response**: `200 OK`
  ```json
  {
    "id": 5,
    "resume_id": 10,
    "analysis_status": "completed",
    "model_name": "gemini-3.5-flash-lite",
    "prompt_version": "v1.0",
    "analysis_error": null,
    "compatibility_score": 82,
    "section_score": 85,
    "impact_score": 78,
    "formatting_score": 86,
    "summary": "Demonstrates strong full-stack software engineering background with quantifiable achievements.",
    "identified_sections": ["contact", "experience", "education", "skills", "projects"],
    "skills_categorized": {
      "Backend": ["Python", "FastAPI", "PostgreSQL"],
      "Frontend": ["React", "TypeScript", "Tailwind CSS"],
      "DevOps & Tools": ["Docker", "Git", "GitHub Actions"]
    },
    "strengths": [
      "Quantifiable performance achievements across software delivery lifecycle",
      "Diverse modern technical stack aligned with senior engineering requirements"
    ],
    "improvements": [
      {
        "category": "Impact",
        "issue": "Some project bullet points focus on responsibilities rather than business outcomes.",
        "recommendation": "Incorporate measurable business metrics into project descriptions.",
        "example": "Changed: 'Built microservice' to 'Architected microservice reducing query latency by 45%'."
      }
    ],
    "suggested_roles": [
      "Senior Full-Stack Engineer",
      "Backend Software Engineer"
    ],
    "missing_or_uncertain_elements": [],
    "scoring_breakdown": {
      "candidate_type": "experienced",
      "section_factors": [
        {
          "name": "Work Experience Section",
          "score": 90,
          "weight": 0.3,
          "explanation": "Clear chronological progression with verified company roles."
        }
      ],
      "impact_factors": [
        {
          "name": "Quantifiable Metrics",
          "score": 75,
          "weight": 0.25,
          "explanation": "Found 8 measurable metric points across experience descriptions."
        }
      ],
      "formatting_factors": [
        {
          "name": "Contact & Layout",
          "score": 85,
          "weight": 0.2,
          "explanation": "All essential contact details and clear headings recognized."
        }
      ],
      "general_notes": []
    },
    "created_at": "2026-11-09T00:00:00Z",
    "updated_at": null
  }
  ```

- **Errors**:
  - `400 Bad Request`: Resume has no extracted text or is in failed status.
  - `404 Not Found`: Resume ID not found.
  - `422 Unprocessable Entity`: `resume_id` is non-positive.
  - `500 Internal Server Error`: Generic internal server error message.

---

### 6.2 Get Resume Analysis
- **Endpoint**: `GET /api/resumes/{resume_id}/analysis`
- **Description**: Retrieves existing analysis record for the specified resume.
- **Path Parameters**:
  | Parameter | Type | Constraint | Description |
  |---|---|---|---|
  | `resume_id` | `integer` | `> 0` | Resume unique identifier |
- **Response**: `200 OK` (returns `ResumeAnalysisResponse` object as documented in 6.1).
- **Errors**:
  - `404 Not Found`: No analysis exists yet for this resume.
  - `422 Unprocessable Entity`: `resume_id` is non-positive.

---

## 7. Status Codes & Error Reference

| HTTP Code | Name | Typical Trigger |
|---|---|---|
| `200 OK` | Successful retrieval, analysis execution, or update | Standard successful GET / POST |
| `201 Created` | Resource created | `POST /api/candidates/`, `POST /api/resumes/upload` |
| `204 No Content` | Successful deletion | `DELETE /api/resumes/{resume_id}` |
| `400 Bad Request` | Duplicate email, invalid file format, or corrupted content | File type mismatch or DB uniqueness violation |
| `404 Not Found` | Candidate, Resume, or Analysis record not found | Invalid or missing ID |
| `413 Payload Too Large` | Upload file exceeds `MAX_FILE_SIZE_BYTES` (5 MB) | Resume upload size limit exceeded |
| `422 Unprocessable Entity` | Pydantic schema validation failure | Non-positive ID, missing field, malformed email |
| `500 Internal Server Error` | Unhandled internal server error | Unexpected runtime fault |

