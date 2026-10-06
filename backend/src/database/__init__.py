#!/usr/bin/env python3
"""
Database Package Initialization

Provides high-level database operations and initialization for the todo application.
"""

from .engine import database_engine, get_engine
from .session import DatabaseSession, get_database_session, get_session
from .migration import MigrationStrategy, run_migration, get_default_sqlite_path
from .indexes import IndexManager, setup_database_indexes, validate_database_indexes, analyze_database_performance

# Database initialization function
def initialize_database(create_tables: bool = True, create_indexes: bool = True) -> None:
    """
    Initialize database with tables and indexes.

    Args:
        create_tables: Whether to create database tables
        create_indexes: Whether to create database indexes
    """
    # Test database connection
    if not database_engine.test_connection():
        raise ConnectionError("Failed to connect to database")

    # Create tables
    if create_tables:
        print("Creating database tables...")
        database_engine.create_all_tables()

    # Create indexes
    if create_indexes:
        print("Creating database indexes...")
        with database_engine.get_session() as session:
            setup_database_indexes(session)

    print("Database initialization completed successfully")


# Migration function
def migrate_from_sqlite(sqlite_path: str = None, postgres_url: str = None) -> dict:
    """
    Migrate data from SQLite to PostgreSQL.

    Args:
        sqlite_path: Path to SQLite database file
        postgres_url: PostgreSQL connection URL

    Returns:
        Migration results and statistics
    """
    return run_migration(sqlite_path, postgres_url)


# Validation function
def validate_database_setup() -> dict:
    """
    Validate database setup including tables and indexes.

    Returns:
        Validation results
    """
    validation_results = {
        'connection': False,
        'tables_exist': False,
        'indexes_valid': True,
        'missing_indexes': []
    }

    # Test connection
    validation_results['connection'] = database_engine.test_connection()

    if validation_results['connection']:
        # Check tables exist
        from sqlmodel import SQLModel
        with database_engine.get_session() as session:
            from sqlalchemy import inspect
            inspector = inspect(session.get_bind())
            existing_tables = inspector.get_table_names()

            required_tables = ['users', 'tasks']
            validation_results['tables_exist'] = all(table in existing_tables for table in required_tables)

            # Validate indexes
            missing_indexes = validate_database_indexes(session)
            validation_results['missing_indexes'] = missing_indexes
            validation_results['indexes_valid'] = len(missing_indexes) == 0

    return validation_results


__all__ = [
    'database_engine',
    'get_engine',
    'DatabaseSession',
    'get_database_session',
    'get_session',
    'MigrationStrategy',
    'run_migration',
    'get_default_sqlite_path',
    'IndexManager',
    'setup_database_indexes',
    'validate_database_indexes',
    'analyze_database_performance',
    'initialize_database',
    'migrate_from_sqlite',
    'validate_database_setup'
]