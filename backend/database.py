"""
SQLAlchemy database session management.

This module provides database connection and session management for the AI Assistant backend.
It uses SQLAlchemy with SQLite and handles proper path resolution for the database file.
"""

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///../ai-assistant.db")

# Convert relative paths to absolute paths for SQLite
if DATABASE_URL.startswith("sqlite:///"):
    # Extract the file path part
    db_path = DATABASE_URL.replace("sqlite:///", "")

    # If it's a relative path (starts with ../ or ./), make it absolute
    if db_path.startswith("../") or db_path.startswith("./"):
        # Resolve relative to the backend directory
        backend_dir = Path(__file__).parent
        absolute_path = (backend_dir / db_path).resolve()
        DATABASE_URL = f"sqlite:///{absolute_path}"

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=os.getenv("DEBUG", "False").lower() == "true",  # Log SQL queries in debug mode
)


# Enable foreign key constraints for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key constraints for SQLite connections."""
    if "sqlite" in DATABASE_URL:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.

    Usage in FastAPI:
        @app.get("/tasks")
        def get_tasks(db: Session = Depends(get_db)):
            return db.query(Task).all()

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database by creating all tables.

    This should be called when the application starts if tables don't exist.
    In production, use Alembic migrations instead.
    """
    Base.metadata.create_all(bind=engine)
