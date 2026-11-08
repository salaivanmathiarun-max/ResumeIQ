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
]
raw_cors = os.getenv("CORS_ORIGINS")
if raw_cors:
    CORS_ORIGINS = [origin.strip() for origin in raw_cors.split(",") if origin.strip()]
else:
    CORS_ORIGINS = DEFAULT_CORS_ORIGINS
