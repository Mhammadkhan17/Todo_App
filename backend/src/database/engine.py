#!/usr/bin/env python3
"""
Database Engine Configuration

Sets up SQLModel engine for PostgreSQL database connection.
Handles connection pooling and database initialization.
"""

import os
from typing import Optional
from sqlmodel import SQLModel, create_engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
from contextlib import contextmanager
import logging

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseEngine:
    """Database engine manager for PostgreSQL with connection pooling."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database engine.

        Args:
            database_url: PostgreSQL connection URL. If None, uses environment variable or default.
        """
        self.database_url = database_url or self._get_database_url()
        self._engine: Optional[Engine] = None

    def _get_database_url(self) -> str:
        """Get database URL from environment or return default."""
        db_url = os.getenv("DATABASE_URL")

        if not db_url:
            # Default PostgreSQL URL for development
            # In production, this should be set via environment variable
            db_url = "postgresql://localhost:5432/todo_app"

        # Ensure we're using PostgreSQL driver
        if db_url.startswith("sqlite"):
            raise ValueError("PostgreSQL database URL required, not SQLite")

        if not db_url.startswith("postgresql"):
            raise ValueError("Only PostgreSQL databases are supported")

        return db_url

    @property
    def engine(self) -> Engine:
        """Get or create database engine."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    def _create_engine(self) -> Engine:
        """Create and configure database engine."""
        # Connection pool settings
        pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 1 hour

        engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,  # Check connections before use
            echo=False,  # Set to True for SQL debugging
            future=True  # Use SQLAlchemy 2.0 style
        )

        logger.info(f"Database engine created with URL: {self.database_url}")
        return engine

    def create_all_tables(self) -> None:
        """Create all database tables."""
        try:
            SQLModel.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

    def drop_all_tables(self) -> None:
        """Drop all database tables (for testing only)."""
        try:
            SQLModel.metadata.drop_all(self.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise

    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions.

        Usage:
            with database_engine.get_session() as session:
                session.add(user)
                session.commit()
        """
        from sqlmodel import Session

        session = Session(self.engine)
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def get_session_factory(self):
        """Get session factory for dependency injection."""
        from sqlmodel import Session

        def get_session():
            with self.get_session() as session:
                yield session

        return get_session

    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            from sqlalchemy import text
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def close(self) -> None:
        """Close database engine and connections."""
        if self._engine:
            self._engine.dispose()
            logger.info("Database engine closed")


def get_engine(database_url: Optional[str] = None) -> DatabaseEngine:
    """Get database engine instance."""
    return DatabaseEngine(database_url)


# Global engine instance
database_engine = get_engine()