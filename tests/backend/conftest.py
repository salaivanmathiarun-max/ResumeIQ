import sys
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base
from app.database.dependencies import get_db
from app.main import app

# Isolated in-memory SQLite database using StaticPool
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    future=True,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all tables in the isolated test database."""
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def isolate_test_upload_dir(tmp_path, monkeypatch):
    """Ensure all uploads during tests use an isolated temporary directory."""
    test_upload_dir = tmp_path / "test_uploads"
    test_upload_dir.mkdir(parents=True, exist_ok=True)
    import app.core.config
    import app.api.routes.resumes
    monkeypatch.setattr(app.core.config, "UPLOAD_DIR", test_upload_dir)
    monkeypatch.setattr(app.api.routes.resumes, "UPLOAD_DIR", test_upload_dir)
    return test_upload_dir


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Provide a transactional database session for each test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Test client with get_db dependency overridden to isolated test database."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
