from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health
from app.api.routes.candidates import router as candidate_router
from app.api.routes.resumes import router as resume_router
from app.api.routes.analyses import router as analysis_router
from app.core.config import CORS_ORIGINS
from app.database import init_db



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables safely on application startup
    init_db()
    yield


app = FastAPI(
    title="ResumeIQ Backend",
    description="AI-powered Resume Analysis and Career Intelligence Platform API",
    version="0.3.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/", tags=["root"])
async def root():
    return {
        "name": "ResumeIQ API",
        "status": "online",
        "docs_url": "/docs",
    }

# Register API routes under /api
app.include_router(health.router, prefix="/api")
app.include_router(candidate_router, prefix="/api")
app.include_router(resume_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")

