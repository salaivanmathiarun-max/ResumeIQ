# ResumeIQ

**ResumeIQ** is a production-grade, AI-powered Resume Analysis and Career Intelligence Platform. It combines candidate-type-aware deterministic scoring with Google Gemini semantic intelligence and deterministic skill grounding to evaluate resumes with high accuracy, zero hallucinated skills, and transparent feedback.

---

## Key Features

* **Candidate-Type Aware Evaluation**: Tailored scoring models and prompt calibration for **Student**, **Fresher**, and **Experienced** candidates. Students are not penalized for lacking commercial experience or multi-million dollar business metrics.
* **Deterministic Scoring Engine (0–100)**: Transparent sub-scores across Section Completeness, Action Verbs & Measurable Metrics, and Document Formatting & Structure with factor explanations.
* **Google Gemini Semantic Intelligence**: Powered by `gemini-3.5-flash-lite`, generating executive summaries, anchored strengths (`[Project/Role]: Statement`), actionable improvements with before-and-after examples, calibrated job role recommendations, and candidate-appropriate missing elements.
* **Evidence-Based Skill Grounding**: Deterministically verifies all AI-extracted skills against original resume text:
  * Strict boundary matching with a curated tech alias dictionary.
  * Safeguards for short/ambiguous languages (`Go`, `C`, `R`, `TS`).
  * Verbatim snippet verification and substantive domain relevance checks for contextual skills.
  * Automatic dropping of unsupported skills and empty skill categories.
* **Robust Document Parsing**: Native client-side drag-and-drop supporting `.pdf` and `.docx` up to 5 MB with signature verification, de-hyphenation, and structural paragraph normalization.
* **Resilient Full-Stack Architecture**: React 18 dashboard, collapsible analysis breakdowns, single-record retry idempotency, SQLite foreign key cascade consistency, path traversal guards, and automatic API key redaction.

---

## Technology Stack

### Backend
* **Runtime**: Python 3.12
* **Web Framework**: FastAPI (ASGI) + Uvicorn
* **Database & ORM**: SQLite + SQLAlchemy 2.0 (`Mapped` / `mapped_column`)
* **Data Validation**: Pydantic v2
* **Document Processing**: PyMuPDF (`fitz`), `python-docx`
* **AI Engine**: Google GenAI SDK (`google-genai`), `gemini-3.5-flash-lite`
* **Testing**: Pytest (75 tests across 10 modules), HTTPX TestClient

### Frontend
* **Core**: React 18.2.0, Vite 5.2.0
* **Routing**: React Router DOM 6.22.0
* **Styling**: Tailwind CSS 3.4.1, PostCSS, Autoprefixer
* **Icons & Visualization**: Lucide React 0.363.0, Recharts 2.12.3

---

## Project Structure

```text
ResumeIQ/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── analyses.py          # Trigger & retrieve resume analyses (/api/resumes/{id}/analyze)
│   │   │       ├── candidates.py        # Candidate registration & listing (/api/candidates)
│   │   │       ├── health.py            # Health check endpoint (/api/health)
│   │   │       └── resumes.py           # Document upload & text retrieval (/api/resumes)
│   │   ├── core/
│   │   │   └── config.py                # Environment configuration, limits & CORS
│   │   ├── database/
│   │   │   ├── __init__.py              # SQLAlchemy engine, sessionmaker, SQLite PRAGMA listener
│   │   │   └── dependencies.py          # Database session dependency (get_db)
│   │   ├── models/
│   │   │   ├── analysis.py              # ResumeAnalysis SQLAlchemy model
│   │   │   ├── candidate.py             # Candidate SQLAlchemy model
│   │   │   └── resume.py                # Resume SQLAlchemy model
│   │   ├── schemas/
│   │   │   ├── analysis.py              # Pydantic v2 schemas for scoring & AI analysis
│   │   │   ├── candidate.py             # Pydantic v2 schemas for candidates
│   │   │   └── resume.py                # Pydantic v2 schemas for document metadata & text
│   │   ├── services/
│   │   │   ├── analysis_orchestrator.py # Analysis lifecycle coordinator (scoring + Gemini + grounding)
│   │   │   ├── document_parser.py       # PDF/DOCX binary validation & text extraction
│   │   │   ├── gemini_service.py        # Gemini client, structured output schemas, retries & prompt logic
│   │   │   ├── scoring_engine.py        # Deterministic scoring engine (sections, impact, formatting)
│   │   │   └── skill_grounding.py       # Evidence-based skill verification & anti-hallucination engine
│   │   └── main.py                      # FastAPI application entrypoint, CORS & lifespan
│   ├── requirements.txt                 # Backend Python dependencies
│   ├── resumeiq.db                      # SQLite database file
│   ├── uploads/                         # Secure local document storage (UUID-named)
│   └── .env.example                     # Environment variables configuration template
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js                # Centralized API service layer
│   │   ├── components/
│   │   │   ├── common/                  # Reusable UI primitives (Button, Card, Badge, Modal, etc.)
│   │   │   ├── layout/                  # Layout, Header, and Sidebar (with health indicator)
│   │   │   └── upload/                  # FileDropzone (drag-and-drop, validation, progress)
│   │   ├── context/
│   │   │   └── CandidateContext.jsx     # Active candidate state & localStorage synchronization
│   │   ├── pages/
│   │   │   ├── CandidateProfile.jsx     # Candidate registration & switcher
│   │   │   ├── Dashboard.jsx            # SaaS metrics, connectivity status & quick actions
│   │   │   ├── ResumeDetails.jsx        # Compatibility scores, grounded skills, strengths, improvements
│   │   │   ├── ResumeHistory.jsx        # Document library with format filtering and deletion
│   │   │   └── ResumeUpload.jsx         # Upload workspace with immediate text extraction
│   │   ├── App.jsx                      # Router & Application context provider
│   │   ├── index.css                    # Tailwind CSS directives & custom styling
│   │   └── main.jsx                     # React root bootstrap
│   ├── index.html
│   ├── package.json
│   └── vite.config.js                   # Vite dev server configuration with /api proxy to 8000
├── tests/
│   └── backend/                         # 75 automated backend tests across 10 modules
│       ├── conftest.py                  # Isolated in-memory SQLite fixtures & temp directory
│       ├── test_analysis_edge_cases.py  # P0/P1/P2 edge cases (fairness, 5,000-word stress, unicode)
│       ├── test_analysis_routes.py      # Analysis route integration tests
│       ├── test_candidate.py            # Candidate CRUD & validation tests
│       ├── test_gemini_schemas.py       # Pydantic schema validation & bounds tests
│       ├── test_health.py               # Health & root endpoint tests
│       ├── test_resume.py               # Resume CRUD lifecycle tests
│       ├── test_resume_upload.py        # Upload integrity, MIME validation, text normalization
│       ├── test_scoring.py              # Deterministic scoring, action verbs & metrics
│       ├── test_security_and_reliability.py # Path traversal, symlink, retry & sanitization tests
│       └── test_skill_grounding.py      # Grounding engine, short-name protection & alias tests
├── API_DOCUMENTATION.md                 # Complete 13-route REST API reference
├── ARCHITECTURE.md                      # System architecture, Mermaid diagrams & data flow
├── TESTING.md                           # Test suite details, execution guide & coverage breakdown
└── README.md
```

---

## Prerequisites

* **Python**: `3.12`
* **Node.js**: `v20+` (LTS recommended)
* **npm**: `v10+`
* **Google Gemini API Key**: Free tier or paid API key from [Google AI Studio](https://aistudio.google.com/)

---

## Installation & Setup

### 1. Clone & Navigate to Project
```bash
git clone https://github.com/your-username/ResumeIQ.git
cd ResumeIQ
```

### 2. Backend Setup
```powershell
# Navigate to backend directory
cd backend

# Create Python 3.12 virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
Copy-Item .env.example .env
```

Open `backend/.env` and insert your Gemini API key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### 3. Frontend Setup
```powershell
# In a separate terminal, navigate to frontend directory
cd frontend

# Install npm dependencies
npm install
```

---

## Running the Application

### 1. Start the Backend Server
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The FastAPI backend will start at `http://127.0.0.1:8000`.
Interactive Swagger API documentation is available at `http://127.0.0.1:8000/docs`.

### 2. Start the Frontend Development Server
```powershell
cd frontend
npm run dev
```
The React Vite frontend will be accessible at `http://localhost:5173`.

---

## User Workflow

1. **Register Candidate**: Navigate to **Candidates** (`/profile`). Enter the candidate's name, email, and select their seniority tier (`Student`, `Fresher`, or `Experienced`). Click **Set Active**.
2. **Upload Resume**: Navigate to **Upload** (`/upload`). Drag and drop a `.pdf` or `.docx` resume (up to 5 MB). The backend validates the binary signature, extracts the plain text, and stores the document securely.
3. **Run Analysis**: On the **Resume Details** page (`/resumes/:id`), click **Run Analysis** (or **Retry Analysis**). 
4. **Review Results**:
   * **Overall Resume Compatibility Score** with Section, Impact, and Formatting breakdown.
   * **Categorized Skills**: Verified Explicit skills and Contextual skills (with verbatim evidence).
   * **Anchored Strengths**: Each strength cites the specific project, role, or metric anchor.
   * **Actionable Improvements**: Concrete issues paired with recommendations and before-and-after examples.
   * **Calibrated Roles & Missing Elements**: Seniority-appropriate job targets and candidate-level gap indicators.

---

## Implemented API Endpoints (13 Routes)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Root service status and documentation link |
| `GET` | `/api/health` | Service health status check |
| `POST` | `/api/candidates/` | Register a new candidate profile |
| `GET` | `/api/candidates/` | List all candidate profiles |
| `GET` | `/api/candidates/{candidate_id}` | Retrieve a specific candidate profile |
| `POST` | `/api/resumes/upload` | Upload `.pdf` or `.docx`, validate, and extract text |
| `POST` | `/api/resumes/` | Directly create resume metadata record |
| `GET` | `/api/resumes/` | List all uploaded resumes |
| `GET` | `/api/resumes/{resume_id}` | Retrieve resume metadata |
| `GET` | `/api/resumes/{resume_id}/text` | Retrieve raw extracted and normalized plain text |
| `DELETE` | `/api/resumes/{resume_id}` | Safely delete resume and on-disk file |
| `POST` | `/api/resumes/{resume_id}/analyze` | Trigger or retry deterministic and AI analysis |
| `GET` | `/api/resumes/{resume_id}/analysis` | Retrieve complete scoring and semantic analysis data |

*For complete request schemas, parameters, and response structures, see [API_DOCUMENTATION.md](API_DOCUMENTATION.md).*

---

## Automated Testing & Production Build

### Running Backend Tests (75 Passing Tests)
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest tests/backend -v
```
All tests run against an isolated in-memory SQLite database (`sqlite:///:memory:`) and temporary mock directories. Real user databases are never modified.

### Building Frontend for Production
```powershell
cd frontend
npm run build
```
Production output is generated into `frontend/dist/`.

---

## Further Documentation

* **[ARCHITECTURE.md](ARCHITECTURE.md)**: System design, Mermaid architecture diagrams, ERD, and intelligence pipeline specifications.
* **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)**: Detailed specifications for all 13 REST API endpoints.
* **[TESTING.md](TESTING.md)**: Automated testing suite breakdown, edge-case coverage, and security tests.

---

## License

This project is licensed under the MIT License.
