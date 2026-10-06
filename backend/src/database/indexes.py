#!/usr/bin/env python3
"""
Database Index Management

Creates and manages database indexes for optimal query performance.
Handles index creation, validation, and maintenance.
"""

from typing import List, Dict, Any
from sqlmodel import Session, select, text
from sqlalchemy import Index, MetaData, inspect
from sqlalchemy.exc import SQLAlchemyError

from ..models.user import User
from ..models.task import Task, Priority, Status


class IndexManager:
    """Manages database indexes for performance optimization."""

    def __init__(self, session: Session):
        """
        Initialize index manager.

        Args:
            session: Database session
        """
        self.session = session
        self.metadata = MetaData()

    def create_task_indexes(self) -> List[str]:
        """Create indexes for Task table."""
        indexes_created = []

        # Index on user_id for user-specific queries
        try:
            self.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks (user_id)"
            ))
            indexes_created.append("idx_tasks_user_id")
        except SQLAlchemyError as e:
            print(f"Failed to create idx_tasks_user_id: {e}")

        # Composite index on user_id and status for filtered queries
        try:
            self.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON tasks (user_id, status)"
            ))
            indexes_created.append("idx_tasks_user_status")
        except SQLAlchemyError as e:
            print(f"Failed to create idx_tasks_user_status: {e}")

        # Composite index on user_id and priority for priority-based queries
        try:
            self.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_tasks_user_priority ON tasks (user_id, priority)"
            ))
            indexes_created.append("idx_tasks_user_priority")
        except SQLAlchemyError as e:
            print(f"Failed to create idx_tasks_user_priority: {e}")

        # Index on due_date for overdue task queries
        try:
            self.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks (due_date)"
            ))
            indexes_created.append("idx_tasks_due_date")
        except SQLAlchemyError as e:
            print(f"Failed to create idx_tasks_due_date: {e}")

        # Composite index on user_id, status, and due_date for complex queries
        try:
            self.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_tasks_user_status_due ON tasks (user_id, status, due_date)"
            ))
            indexes_created.append("idx_tasks_user_status_due")
        except SQLAlchemyError as e:
            print(f"Failed to create idx_tasks_user_status_due: {e}")

        # Index on created_at for chronological ordering
        try:
            self.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks (created_at)"
            ))
            indexes_created.append("idx_tasks_created_at")
        except SQLAlchemyError as e:
            print(f"Failed to create idx_tasks_created_at: {e}")

        # Index on updated_at for modification tracking
        try:
            self.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks (updated_at)"
            ))
            indexes_created.append("idx_tasks_updated_at")
        except SQLAlchemyError as e:
            print(f"Failed to create idx_tasks_updated_at: {e}")

        return indexes_created

    def create_user_indexes(self) -> List[str]:
        """Create indexes for User table."""
        indexes_created = []

        # Unique index on email (already defined in model, but ensure it exists)
        try:
            self.session.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users (email)"
            ))
            indexes_created.append("idx_users_email")
        except SQLAlchemyError as e:
            print(f"Failed to create idx_users_email: {e}")

        # Unique index on username (already defined in model, but ensure it exists)
        try:
            self.session.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users (username)"
            ))
            indexes_created.append("idx_users_username")
        except SQLAlchemyError as e:
            print(f"Failed to create idx_users_username: {e}")

        # Index on created_at for user registration queries
        try:
            self.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at)"
            ))
            indexes_created.append("idx_users_created_at")
        except SQLAlchemyError as e:
            print(f"Failed to create idx_users_created_at: {e}")

        # Index on last_login_at for activity tracking
        try:
            self.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_users_last_login ON users (last_login_at)"
            ))
            indexes_created.append("idx_users_last_login")
        except SQLAlchemyError as e:
            print(f"Failed to create idx_users_last_login: {e}")

        # Composite index on email_verified and created_at for verification queries
        try:
            self.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_users_verified_created ON users (email_verified, created_at)"
            ))
            indexes_created.append("idx_users_verified_created")
        except SQLAlchemyError as e:
            print(f"Failed to create idx_users_verified_created: {e}")

        return indexes_created

    def create_all_indexes(self) -> Dict[str, List[str]]:
        """Create all recommended indexes."""
        task_indexes = self.create_task_indexes()
        user_indexes = self.create_user_indexes()

        return {
            'task_indexes': task_indexes,
            'user_indexes': user_indexes
        }

    def get_existing_indexes(self) -> Dict[str, List[str]]:
        """Get all existing indexes in the database."""
        inspector = inspect(self.session.get_bind())
        indexes_by_table = {}

        # Get all tables
        tables = inspector.get_table_names()

        for table_name in tables:
            indexes = inspector.get_indexes(table_name)
            indexes_by_table[table_name] = [idx['name'] for idx in indexes]

        return indexes_by_table

    def analyze_index_usage(self) -> Dict[str, Any]:
        """Analyze index usage (PostgreSQL specific)."""
        analysis = {}

        try:
            # Get index usage statistics
            result = self.session.execute(text("""
                SELECT
                    t.tablename,
                    indexname,
                    c.reltuples AS num_rows,
                    pg_size_pretty(pg_total_relation_size(c.oid)) AS table_size,
                    pg_size_pretty(pg_relation_size(c.oid)) AS table_size_raw,
                    pg_size_pretty(pg_relation_size(con.relid)) AS index_size,
                    idx_tup_read,
                    idx_tup_fetch,
                    idx_scan
                FROM pg_tables t
                LEFT OUTER JOIN pg_class c ON c.relname = t.tablename
                LEFT OUTER JOIN (
                    SELECT c.relname AS ctablename, ipg.relname AS indexname, x.indnatts AS number_of_columns,
                           idx_tup_read, idx_tup_fetch, idx_scan
                    FROM pg_index x
                    JOIN pg_class c ON c.oid = x.indrelid
                    JOIN pg_class ipg ON ipg.oid = x.indexrelid
                    JOIN pg_stat_user_indexes psui ON x.indexrelid = psui.indexrelid
                ) AS foo ON t.tablename = foo.ctablename
                WHERE t.schemaname = 'public'
                ORDER BY 1, 2;
            """))

            analysis['index_usage'] = [dict(row) for row in result.fetchall()]

        except SQLAlchemyError as e:
            analysis['error'] = f"Index usage analysis failed: {e}"

        return analysis

    def validate_indexes(self) -> Dict[str, List[str]]:
        """Validate that all recommended indexes exist."""
        existing_indexes = self.get_existing_indexes()

        required_indexes = {
            'tasks': [
                'idx_tasks_user_id',
                'idx_tasks_user_status',
                'idx_tasks_user_priority',
                'idx_tasks_due_date',
                'idx_tasks_user_status_due',
                'idx_tasks_created_at',
                'idx_tasks_updated_at'
            ],
            'users': [
                'idx_users_email',
                'idx_users_username',
                'idx_users_created_at',
                'idx_users_last_login',
                'idx_users_verified_created'
            ]
        }

        missing_indexes = {}
        for table, indexes in required_indexes.items():
            existing = existing_indexes.get(table, [])
            missing = [idx for idx in indexes if idx not in existing]
            if missing:
                missing_indexes[table] = missing

        return missing_indexes

    def rebuild_indexes(self) -> Dict[str, List[str]]:
        """Rebuild all indexes (PostgreSQL specific)."""
        rebuilt_indexes = []

        try:
            # Get all indexes
            existing_indexes = self.get_existing_indexes()

            for table, indexes in existing_indexes.items():
                for index_name in indexes:
                    try:
                        self.session.execute(text(f"REINDEX INDEX {index_name}"))
                        rebuilt_indexes.append(index_name)
                    except SQLAlchemyError as e:
                        print(f"Failed to rebuild index {index_name}: {e}")

        except SQLAlchemyError as e:
            print(f"Index rebuild failed: {e}")

        return {'rebuilt_indexes': rebuilt_indexes}

    def drop_unused_indexes(self, unused_indexes: List[str]) -> List[str]:
        """Drop specified unused indexes."""
        dropped_indexes = []

        for index_name in unused_indexes:
            try:
                self.session.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
                dropped_indexes.append(index_name)
                print(f"Dropped unused index: {index_name}")
            except SQLAlchemyError as e:
                print(f"Failed to drop index {index_name}: {e}")

        return dropped_indexes


def setup_database_indexes(session: Session) -> Dict[str, List[str]]:
    """Setup all recommended database indexes."""
    index_manager = IndexManager(session)
    return index_manager.create_all_indexes()


def validate_database_indexes(session: Session) -> Dict[str, List[str]]:
    """Validate that all required indexes exist."""
    index_manager = IndexManager(session)
    return index_manager.validate_indexes()


def analyze_database_performance(session: Session) -> Dict[str, Any]:
    """Analyze database performance and index usage."""
    index_manager = IndexManager(session)
    return index_manager.analyze_index_usage()


if __name__ == "__main__":
    # Example usage
    from ..database.engine import database_engine

    with database_engine.get_session() as session:
        # Setup indexes
        indexes = setup_database_indexes(session)
        print(f"Created indexes: {indexes}")

        # Validate indexes
        missing = validate_database_indexes(session)
        if missing:
            print(f"Missing indexes: {missing}")
        else:
            print("All required indexes exist")

        # Analyze performance
        analysis = analyze_database_performance(session)
        print(f"Index analysis: {analysis}")