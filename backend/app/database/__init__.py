import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraint enforcement only for SQLite connections."""
    try:
        if dbapi_connection.__class__.__module__.startswith("sqlite"):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    except Exception:
        pass

# Base directory of the project (backend folder)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Configurable database connection
raw_db_url = os.getenv("DATABASE_URL")
if raw_db_url:
    # Normalize postgres:// to postgresql:// for SQLAlchemy compatibility
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URL = raw_db_url
else:
    # Configurable SQLite database path (supports persistent volume mount e.g. /data/resumeiq.db)
    sqlite_custom_path = os.getenv("SQLITE_DB_PATH")
    if sqlite_custom_path:
        SQLITE_DB_PATH = Path(sqlite_custom_path)
    else:
        SQLITE_DB_PATH = BASE_DIR / "resumeiq.db"
    SQLALCHEMY_DATABASE_URL = f"sqlite+pysqlite:///{SQLITE_DB_PATH}?check_same_thread=False"

connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
    future=True,
    connect_args=connect_args,
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""
    pass


def init_db():
    """Import models to register them with Base.metadata and create tables safely."""
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
