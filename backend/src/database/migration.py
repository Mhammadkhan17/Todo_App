#!/usr/bin/env python3
"""
Database Migration Strategy

Migration plan from Phase 1 SQLite to Phase 2 PostgreSQL.
Handles data transformation and migration between database systems.
"""

import sqlite3
import os
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select, create_engine
from sqlalchemy import text

from ..models.user import User
from ..models.task import Task, Priority, Status
from .engine import get_engine


class MigrationStrategy:
    """Handles migration from SQLite to PostgreSQL."""

    def __init__(self, sqlite_path: str, postgres_engine):
        """
        Initialize migration strategy.

        Args:
            sqlite_path: Path to SQLite database file
            postgres_engine: PostgreSQL engine instance
        """
        self.sqlite_path = sqlite_path
        self.postgres_engine = postgres_engine

    def validate_sqlite_database(self) -> bool:
        """Validate that SQLite database exists and has required tables."""
        if not os.path.exists(self.sqlite_path):
            raise FileNotFoundError(f"SQLite database not found: {self.sqlite_path}")

        with sqlite3.connect(self.sqlite_path) as conn:
            cursor = conn.cursor()

            # Check if tasks table exists
            cursor.execute("""
                SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'
            """)
            if not cursor.fetchone():
                raise ValueError("Tasks table not found in SQLite database")

            # Check required columns
            cursor.execute("PRAGMA table_info(tasks)")
            columns = [row[1] for row in cursor.fetchall()]

            required_columns = ['title', 'description', 'priority', 'due_date', 'completed']
            missing_columns = [col for col in required_columns if col not in columns]

            if missing_columns:
                raise ValueError(f"Missing required columns in SQLite tasks table: {missing_columns}")

        return True

    def read_sqlite_data(self) -> List[Dict[str, Any]]:
        """Read all tasks from SQLite database."""
        tasks = []

        with sqlite3.connect(self.sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks ORDER BY created_at")

            for row in cursor.fetchall():
                task_data = dict(row)
                tasks.append(task_data)

        return tasks

    def transform_task_data(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform SQLite task data to PostgreSQL format."""
        transformed = {}

        # Basic fields
        transformed['title'] = task_data['title']

        if task_data['description']:
            transformed['description'] = task_data['description']
        else:
            transformed['description'] = None

        # Priority mapping
        priority_map = {
            'high': Priority.HIGH,
            'medium': Priority.MEDIUM,
            'low': Priority.LOW
        }
        transformed['priority'] = priority_map.get(task_data['priority'], Priority.MEDIUM)

        # Due date transformation
        if task_data['due_date']:
            try:
                # Parse date from SQLite format (YYYY-MM-DD)
                transformed['due_date'] = date.fromisoformat(task_data['due_date'])
            except ValueError:
                transformed['due_date'] = None
        else:
            transformed['due_date'] = None

        # Status mapping
        if task_data['completed']:
            transformed['status'] = Status.COMPLETED
            transformed['completed_at'] = datetime.strptime(
                task_data.get('updated_at', datetime.utcnow().isoformat()),
                '%Y-%m-%d %H:%M:%S.%f' if '.' in str(task_data.get('updated_at', '')) else '%Y-%m-%d %H:%M:%S'
            )
        else:
            transformed['status'] = Status.ACTIVE
            transformed['completed_at'] = None

        # Timestamps
        created_at = task_data.get('created_at')
        updated_at = task_data.get('updated_at')

        if created_at:
            try:
                transformed['created_at'] = datetime.strptime(
                    created_at,
                    '%Y-%m-%d %H:%M:%S.%f' if '.' in str(created_at) else '%Y-%m-%d %H:%M:%S'
                )
            except ValueError:
                transformed['created_at'] = datetime.utcnow()
        else:
            transformed['created_at'] = datetime.utcnow()

        if updated_at:
            try:
                transformed['updated_at'] = datetime.strptime(
                    updated_at,
                    '%Y-%m-%d %H:%M:%S.%f' if '.' in str(updated_at) else '%Y-%m-%d %H:%M:%S'
                )
            except ValueError:
                transformed['updated_at'] = transformed['created_at']
        else:
            transformed['updated_at'] = transformed['created_at']

        return transformed

    def create_default_user(self, session: Session) -> User:
        """Create a default user for migrating tasks."""
        from sqlalchemy.exc import IntegrityError

        # Check if default user already exists
        default_user = session.exec(
            select(User).where(User.email == "migrated@todoapp.com")
        ).first()

        if default_user:
            return default_user

        # Create default user
        user = User(
            email="migrated@todoapp.com",
            username="migrated_user",
            password_hash="$2b$12$dummy_hash_for_migration",  # Dummy hash
            full_name="Migrated User",
            is_active=True,
            email_verified=True
        )

        try:
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
        except IntegrityError:
            session.rollback()
            # User might exist with different email, try to find any user
            existing_user = session.exec(select(User)).first()
            if existing_user:
                return existing_user
            raise

    def migrate_tasks(self) -> Dict[str, int]:
        """Migrate all tasks from SQLite to PostgreSQL."""
        migration_stats = {
            'total_tasks': 0,
            'successful_migrations': 0,
            'failed_migrations': 0,
            'skipped_tasks': 0
        }

        # Read SQLite data
        sqlite_tasks = self.read_sqlite_data()
        migration_stats['total_tasks'] = len(sqlite_tasks)

        if not sqlite_tasks:
            return migration_stats

        # Get or create default user
        with self.postgres_engine.get_session() as session:
            default_user = self.create_default_user(session)

            for task_data in sqlite_tasks:
                try:
                    # Transform task data
                    transformed_data = self.transform_task_data(task_data)

                    # Create new task
                    task = Task(
                        title=transformed_data['title'],
                        description=transformed_data['description'],
                        priority=transformed_data['priority'],
                        due_date=transformed_data['due_date'],
                        status=transformed_data['status'],
                        created_at=transformed_data['created_at'],
                        updated_at=transformed_data['updated_at'],
                        completed_at=transformed_data['completed_at'],
                        user_id=default_user.id
                    )

                    session.add(task)
                    session.commit()
                    session.refresh(task)

                    migration_stats['successful_migrations'] += 1

                except Exception as e:
                    session.rollback()
                    migration_stats['failed_migrations'] += 1
                    print(f"Failed to migrate task '{task_data.get('title', 'Unknown')}': {e}")

        return migration_stats

    def verify_migration(self) -> Dict[str, Any]:
        """Verify migration results."""
        with self.postgres_engine.get_session() as session:
            total_tasks = session.exec(select(Task)).count()
            active_tasks = session.exec(
                select(Task).where(Task.status == Status.ACTIVE)
            ).count()
            completed_tasks = session.exec(
                select(Task).where(Task.status == Status.COMPLETED)
            ).count()

            users = session.exec(select(User)).count()

        return {
            'total_tasks': total_tasks,
            'active_tasks': active_tasks,
            'completed_tasks': completed_tasks,
            'users': users,
            'verification_timestamp': datetime.utcnow().isoformat()
        }

    def run_migration(self) -> Dict[str, Any]:
        """Run complete migration process."""
        print("Starting SQLite to PostgreSQL migration...")

        # Validate SQLite database
        print("Validating SQLite database...")
        self.validate_sqlite_database()

        # Run migration
        print("Migrating tasks...")
        migration_stats = self.migrate_tasks()

        # Verify results
        print("Verifying migration results...")
        verification = self.verify_migration()

        result = {
            'migration_started': datetime.utcnow().isoformat(),
            'migration_stats': migration_stats,
            'verification': verification,
            'migration_completed': datetime.utcnow().isoformat()
        }

        print(f"Migration completed. {migration_stats['successful_migrations']} tasks migrated successfully.")
        return result


def get_default_sqlite_path() -> str:
    """Get default SQLite database path from Phase 1."""
    from pathlib import Path
    home = Path.home()
    return str(home / ".todo" / "tasks.db")


def run_migration(sqlite_path: Optional[str] = None, postgres_url: Optional[str] = None) -> Dict[str, Any]:
    """Run migration from SQLite to PostgreSQL."""
    if sqlite_path is None:
        sqlite_path = get_default_sqlite_path()

    postgres_engine = get_engine(postgres_url)

    # Test PostgreSQL connection
    if not postgres_engine.test_connection():
        raise ConnectionError("Failed to connect to PostgreSQL database")

    # Create tables if they don't exist
    postgres_engine.create_all_tables()

    # Run migration
    migration = MigrationStrategy(sqlite_path, postgres_engine)
    result = migration.run_migration()

    return result


if __name__ == "__main__":
    # Example usage
    # python migration.py
    try:
        result = run_migration()
        print(f"Migration successful: {result}")
    except Exception as e:
        print(f"Migration failed: {e}")