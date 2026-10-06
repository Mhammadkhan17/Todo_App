#!/usr/bin/env python3
"""
Database Setup Script

Standalone script for setting up the PostgreSQL database for the todo application.
Can be used for initial setup, migration, or validation.
"""

import os
import sys
import argparse
from pathlib import Path

# Add backend src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import (
    initialize_database,
    migrate_from_sqlite,
    validate_database_setup,
    database_engine
)


def main():
    """Main setup script entry point."""
    parser = argparse.ArgumentParser(description="Setup PostgreSQL database for todo application")
    parser.add_argument('--action', choices=['init', 'migrate', 'validate', 'all'],
                       default='all', help='Action to perform')
    parser.add_argument('--sqlite-path', help='Path to SQLite database file for migration')
    parser.add_argument('--postgres-url', help='PostgreSQL connection URL')
    parser.add_argument('--skip-tables', action='store_true', help='Skip table creation')
    parser.add_argument('--skip-indexes', action='store_true', help='Skip index creation')

    args = parser.parse_args()

    print("Todo Application Database Setup")
    print("=" * 40)

    # Set environment variables if provided
    if args.postgres_url:
        os.environ['DATABASE_URL'] = args.postgres_url

    try:
        if args.action in ['init', 'all']:
            print("\n1. Initializing database...")
            initialize_database(
                create_tables=not args.skip_tables,
                create_indexes=not args.skip_indexes
            )

        if args.action in ['migrate', 'all']:
            print("\n2. Migrating data from SQLite...")
            sqlite_path = args.sqlite_path
            if not sqlite_path:
                from database.migration import get_default_sqlite_path
                sqlite_path = get_default_sqlite_path()
                print(f"Using default SQLite path: {sqlite_path}")

            if os.path.exists(sqlite_path):
                migration_result = migrate_from_sqlite(
                    sqlite_path=sqlite_path,
                    postgres_url=args.postgres_url
                )
                print(f"Migration completed: {migration_result}")
            else:
                print(f"SQLite database not found at: {sqlite_path}")
                print("Skipping migration step.")

        if args.action in ['validate', 'all']:
            print("\n3. Validating database setup...")
            validation = validate_database_setup()

            print(f"Connection: {'✓' if validation['connection'] else '✗'}")
            print(f"Tables exist: {'✓' if validation['tables_exist'] else '✗'}")
            print(f"Indexes valid: {'✓' if validation['indexes_valid'] else '✗'}")

            if validation['missing_indexes']:
                print("Missing indexes:")
                for table, indexes in validation['missing_indexes'].items():
                    for index in indexes:
                        print(f"  - {table}.{index}")

        print("\nDatabase setup completed successfully!")

    except Exception as e:
        print(f"\nError during database setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()