import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR.parent

# Load .env file if present
load_dotenv(BACKEND_DIR / ".env")

# Environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Upload configurations
UPLOAD_DIR = Path(os.getenv("RESUMEIQ_UPLOAD_DIR", str(BACKEND_DIR / "uploads")))
MAX_FILE_SIZE_BYTES = int(os.getenv("MAX_FILE_SIZE_BYTES", str(5 * 1024 * 1024)))  # 5 MB
ALLOWED_FILE_EXTENSIONS = {".pdf", ".docx"}

# CORS configurations
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://resume-iq-olive-theta.vercel.app",
]


def parse_cors_origins(raw: str | None) -> list[str]:
    """Parse and normalize CORS_ORIGINS from raw string, stripping whitespace, quotes, and trailing slashes."""
    if not raw:
        return list(DEFAULT_CORS_ORIGINS)
    parsed = []
    for origin in raw.split(","):
        cleaned = origin.strip().strip("'\"").rstrip("/")
        if cleaned:
            parsed.append(cleaned)
    return parsed if parsed else list(DEFAULT_CORS_ORIGINS)


CORS_ORIGINS = parse_cors_origins(os.getenv("CORS_ORIGINS"))
