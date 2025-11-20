#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - Migration Verification Script
Validates database migrations for correctness and integrity
"""

import sys
import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / 'database' / 'migrations'
TEST_DB_PATH = PROJECT_ROOT / 'database' / 'test_migration_verify.db'


class MigrationVerifier:
    """Verifies database migrations for correctness and integrity."""

    def __init__(self, migrations_dir: Path, test_db_path: Path):
        """
        Initialize migration verifier.

        Args:
            migrations_dir: Path to migrations directory
            test_db_path: Path to temporary test database
        """
        self.migrations_dir = migrations_dir
        self.test_db_path = test_db_path
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }

    def run_all_checks(self) -> bool:
        """
        Run all migration verification checks.

        Returns:
            True if all checks pass
        """
        logger.info("=" * 80)
        logger.info("FRISCO WHISPER RTX 5xxx - Migration Verification")
        logger.info("=" * 80)
        logger.info("")

        checks = [
            ("Migration Files Exist", self.check_migration_files_exist),
            ("Migration Sequence", self.check_migration_sequence),
            ("SQL Syntax", self.check_sql_syntax),
            ("Schema Structure", self.check_schema_structure),
            ("Foreign Keys", self.check_foreign_keys),
            ("Indexes", self.check_indexes),
            ("Triggers", self.check_triggers),
            ("Views", self.check_views),
            ("Migration Idempotency", self.check_idempotency),
            ("Schema Version", self.check_schema_version)
        ]

        all_passed = True

        for check_name, check_func in checks:
            logger.info(f"Running: {check_name}")
            logger.info("-" * 80)

            try:
                success = check_func()
                if success:
                    self.results['passed'].append(check_name)
                    logger.info(f"✓ {check_name}: PASSED")
                else:
                    self.results['failed'].append(check_name)
                    logger.error(f"✗ {check_name}: FAILED")
                    all_passed = False
            except Exception as e:
                self.results['failed'].append(check_name)
                logger.error(f"✗ {check_name}: ERROR - {e}")
                all_passed = False

            logger.info("")

        # Print summary
        self.print_summary()

        # Cleanup
        self.cleanup()

        return all_passed

    def check_migration_files_exist(self) -> bool:
        """Verify migration files exist and are readable."""
        if not self.migrations_dir.exists():
            logger.error(f"Migrations directory not found: {self.migrations_dir}")
            return False

        expected_migrations = [
            '001_initial_schema.sql',
            '002_add_versioning.sql'
        ]

        all_exist = True
        for migration_file in expected_migrations:
            path = self.migrations_dir / migration_file
            if not path.exists():
                logger.error(f"Migration file not found: {migration_file}")
                all_exist = False
            else:
                logger.info(f"  Found: {migration_file}")

        return all_exist

    def check_migration_sequence(self) -> bool:
        """Verify migrations are properly sequenced."""
        migration_files = sorted(self.migrations_dir.glob('*.sql'))

        if not migration_files:
            logger.error("No migration files found")
            return False

        expected_sequence = 1
        for migration_file in migration_files:
            # Extract sequence number from filename (e.g., 001_xxx.sql -> 1)
            match = re.match(r'(\d+)_.*\.sql', migration_file.name)
            if not match:
                logger.error(f"Invalid migration filename format: {migration_file.name}")
                return False

            sequence_num = int(match.group(1))
            if sequence_num != expected_sequence:
                logger.error(
                    f"Migration sequence gap: expected {expected_sequence:03d}, "
                    f"found {sequence_num:03d}"
                )
                return False

            logger.info(f"  {migration_file.name} - Sequence OK")
            expected_sequence += 1

        return True

    def check_sql_syntax(self) -> bool:
        """Verify SQL syntax is valid by executing migrations."""
        # Clean up any existing test database
        if self.test_db_path.exists():
            self.test_db_path.unlink()

        try:
            conn = sqlite3.connect(str(self.test_db_path))
            conn.row_factory = sqlite3.Row

            migration_files = sorted(self.migrations_dir.glob('*.sql'))

            for migration_file in migration_files:
                logger.info(f"  Executing: {migration_file.name}")

                with open(migration_file, 'r', encoding='utf-8') as f:
                    migration_sql = f.read()

                try:
                    conn.executescript(migration_sql)
                    logger.info(f"    ✓ SQL syntax valid")
                except sqlite3.Error as e:
                    logger.error(f"    ✗ SQL syntax error: {e}")
                    conn.close()
                    return False

            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to verify SQL syntax: {e}")
            return False

    def check_schema_structure(self) -> bool:
        """Verify all expected tables exist with correct columns."""
        conn = sqlite3.connect(str(self.test_db_path))
        cursor = conn.cursor()

        expected_tables = {
            'files': [
                'id', 'file_hash', 'original_name', 'file_path',
                'size_bytes', 'format', 'uploaded_at'
            ],
            'transcription_jobs': [
                'job_id', 'file_id', 'file_name', 'model_size', 'status',
                'task_type', 'language', 'detected_language', 'language_probability',
                'compute_type', 'device', 'beam_size', 'created_at', 'updated_at',
                'started_at', 'completed_at', 'duration_seconds',
                'processing_time_seconds', 'error_message'
            ],
            'transcriptions': [
                'id', 'job_id', 'text', 'language', 'segment_count',
                'segments', 'srt_path', 'created_at'
            ],
            'transcript_versions': [
                'version_id', 'transcription_id', 'version_number', 'text',
                'segments', 'segment_count', 'created_at', 'created_by',
                'change_note', 'is_current'
            ],
            'export_formats': [
                'format_id', 'format_name', 'mime_type', 'file_extension',
                'description', 'is_active'
            ],
            'export_history': [
                'export_id', 'transcription_id', 'version_number',
                'format_name', 'file_path', 'exported_at', 'exported_by'
            ],
            'schema_metadata': [
                'key', 'value', 'updated_at'
            ]
        }

        all_tables_valid = True

        for table_name, expected_columns in expected_tables.items():
            # Check table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            result = cursor.fetchone()

            if not result:
                logger.error(f"  ✗ Table not found: {table_name}")
                all_tables_valid = False
                continue

            # Check columns
            cursor.execute(f"PRAGMA table_info({table_name})")
            actual_columns = [row[1] for row in cursor.fetchall()]

            missing_columns = set(expected_columns) - set(actual_columns)
            extra_columns = set(actual_columns) - set(expected_columns)

            if missing_columns:
                logger.error(
                    f"  ✗ {table_name}: Missing columns: {', '.join(missing_columns)}"
                )
                all_tables_valid = False

            if extra_columns:
                logger.warning(
                    f"  ⚠ {table_name}: Extra columns: {', '.join(extra_columns)}"
                )
                self.results['warnings'].append(
                    f"{table_name} has extra columns: {', '.join(extra_columns)}"
                )

            if not missing_columns and not extra_columns:
                logger.info(f"  ✓ {table_name}: All columns present")

        conn.close()
        return all_tables_valid

    def check_foreign_keys(self) -> bool:
        """Verify all foreign key constraints are properly defined."""
        conn = sqlite3.connect(str(self.test_db_path))
        cursor = conn.cursor()

        expected_fks = {
            'transcription_jobs': [
                ('file_id', 'files', 'id')
            ],
            'transcriptions': [
                ('job_id', 'transcription_jobs', 'job_id')
            ],
            'transcript_versions': [
                ('transcription_id', 'transcriptions', 'id')
            ],
            'export_history': [
                ('transcription_id', 'transcriptions', 'id'),
                ('format_name', 'export_formats', 'format_name')
            ]
        }

        all_fks_valid = True

        for table_name, expected_fk_list in expected_fks.items():
            cursor.execute(f"PRAGMA foreign_key_list({table_name})")
            actual_fks = cursor.fetchall()

            # Convert to comparable format
            actual_fk_tuples = set()
            for fk in actual_fks:
                # fk format: (id, seq, table, from, to, on_update, on_delete, match)
                actual_fk_tuples.add((fk[3], fk[2], fk[4]))  # (from, table, to)

            expected_fk_set = set(expected_fk_list)

            if actual_fk_tuples != expected_fk_set:
                logger.error(
                    f"  ✗ {table_name}: Foreign key mismatch\n"
                    f"    Expected: {expected_fk_set}\n"
                    f"    Actual: {actual_fk_tuples}"
                )
                all_fks_valid = False
            else:
                logger.info(
                    f"  ✓ {table_name}: {len(expected_fk_list)} foreign key(s) correct"
                )

        conn.close()
        return all_fks_valid

    def check_indexes(self) -> bool:
        """Verify all expected indexes exist."""
        conn = sqlite3.connect(str(self.test_db_path))
        cursor = conn.cursor()

        expected_indexes = [
            # Files
            'idx_files_hash',
            'idx_files_name',
            'idx_files_uploaded',
            # Jobs
            'idx_jobs_status',
            'idx_jobs_created',
            'idx_jobs_updated',
            'idx_jobs_file_id',
            'idx_jobs_status_created',
            # Transcriptions
            'idx_transcriptions_job',
            'idx_transcriptions_created',
            'idx_transcriptions_language',
            # Versions
            'idx_versions_transcription',
            'idx_versions_number',
            'idx_versions_created',
            'idx_versions_current',
            'idx_versions_trans_num',
            # Exports
            'idx_exports_transcription',
            'idx_exports_format',
            'idx_exports_time'
        ]

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        actual_indexes = {row[0] for row in cursor.fetchall()}

        missing_indexes = set(expected_indexes) - actual_indexes
        extra_indexes = actual_indexes - set(expected_indexes)

        all_indexes_valid = True

        if missing_indexes:
            logger.error(f"  ✗ Missing indexes: {', '.join(sorted(missing_indexes))}")
            all_indexes_valid = False

        if extra_indexes:
            logger.warning(f"  ⚠ Extra indexes: {', '.join(sorted(extra_indexes))}")
            self.results['warnings'].append(
                f"Extra indexes found: {', '.join(sorted(extra_indexes))}"
            )

        if not missing_indexes:
            logger.info(f"  ✓ All {len(expected_indexes)} expected indexes present")

        conn.close()
        return all_indexes_valid

    def check_triggers(self) -> bool:
        """Verify all expected triggers exist."""
        conn = sqlite3.connect(str(self.test_db_path))
        cursor = conn.cursor()

        expected_triggers = [
            'transcriptions_fts_insert',
            'transcriptions_fts_update',
            'transcriptions_fts_delete',
            'update_job_timestamp',
            'create_initial_version',
            'create_version_on_update'
        ]

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        )
        actual_triggers = {row[0] for row in cursor.fetchall()}

        missing_triggers = set(expected_triggers) - actual_triggers
        extra_triggers = actual_triggers - set(expected_triggers)

        all_triggers_valid = True

        if missing_triggers:
            logger.error(
                f"  ✗ Missing triggers: {', '.join(sorted(missing_triggers))}"
            )
            all_triggers_valid = False

        if extra_triggers:
            logger.warning(
                f"  ⚠ Extra triggers: {', '.join(sorted(extra_triggers))}"
            )
            self.results['warnings'].append(
                f"Extra triggers found: {', '.join(sorted(extra_triggers))}"
            )

        if not missing_triggers:
            logger.info(f"  ✓ All {len(expected_triggers)} expected triggers present")

        conn.close()
        return all_triggers_valid

    def check_views(self) -> bool:
        """Verify all expected views exist."""
        conn = sqlite3.connect(str(self.test_db_path))
        cursor = conn.cursor()

        expected_views = [
            'v_job_details',
            'v_job_statistics',
            'v_current_versions',
            'v_version_history',
            'v_export_statistics',
            'v_transcription_version_counts',
            'v_version_diffs'
        ]

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='view'"
        )
        actual_views = {row[0] for row in cursor.fetchall()}

        missing_views = set(expected_views) - actual_views
        extra_views = actual_views - set(expected_views)

        all_views_valid = True

        if missing_views:
            logger.error(f"  ✗ Missing views: {', '.join(sorted(missing_views))}")
            all_views_valid = False

        if extra_views:
            logger.warning(f"  ⚠ Extra views: {', '.join(sorted(extra_views))}")
            self.results['warnings'].append(
                f"Extra views found: {', '.join(sorted(extra_views))}"
            )

        if not missing_views:
            logger.info(f"  ✓ All {len(expected_views)} expected views present")

        conn.close()
        return all_views_valid

    def check_idempotency(self) -> bool:
        """Test that migrations can be run multiple times safely."""
        logger.info("  Testing migration idempotency...")

        try:
            conn = sqlite3.connect(str(self.test_db_path))

            migration_files = sorted(self.migrations_dir.glob('*.sql'))

            for migration_file in migration_files:
                logger.info(f"    Re-running: {migration_file.name}")

                with open(migration_file, 'r', encoding='utf-8') as f:
                    migration_sql = f.read()

                try:
                    # Run migration again
                    conn.executescript(migration_sql)
                    logger.info(f"      ✓ Idempotent execution successful")
                except sqlite3.Error as e:
                    logger.error(f"      ✗ Not idempotent: {e}")
                    conn.close()
                    return False

            conn.close()
            return True

        except Exception as e:
            logger.error(f"Idempotency check failed: {e}")
            return False

    def check_schema_version(self) -> bool:
        """Verify schema version metadata is correct."""
        conn = sqlite3.connect(str(self.test_db_path))
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
            )
            result = cursor.fetchone()

            if not result:
                logger.error("  ✗ Schema version not found in metadata")
                return False

            schema_version = result[0]
            expected_version = '002'  # Current version after all migrations

            if schema_version != expected_version:
                logger.error(
                    f"  ✗ Schema version mismatch: "
                    f"expected '{expected_version}', got '{schema_version}'"
                )
                return False

            logger.info(f"  ✓ Schema version correct: {schema_version}")

            # Check migration timestamp
            cursor.execute(
                "SELECT value FROM schema_metadata WHERE key = 'migration_002_applied_at'"
            )
            result = cursor.fetchone()

            if result:
                logger.info(f"  ✓ Migration 002 timestamp: {result[0]}")
            else:
                logger.warning("  ⚠ Migration 002 timestamp not found")
                self.results['warnings'].append("Migration 002 timestamp missing")

            return True

        except Exception as e:
            logger.error(f"Schema version check failed: {e}")
            return False
        finally:
            conn.close()

    def print_summary(self):
        """Print verification summary."""
        logger.info("=" * 80)
        logger.info("VERIFICATION SUMMARY")
        logger.info("=" * 80)

        total_checks = len(self.results['passed']) + len(self.results['failed'])
        passed_count = len(self.results['passed'])
        failed_count = len(self.results['failed'])
        warning_count = len(self.results['warnings'])

        logger.info(f"Total Checks: {total_checks}")
        logger.info(f"Passed: {passed_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"Warnings: {warning_count}")
        logger.info("")

        if self.results['passed']:
            logger.info("Passed Checks:")
            for check in self.results['passed']:
                logger.info(f"  ✓ {check}")
            logger.info("")

        if self.results['failed']:
            logger.error("Failed Checks:")
            for check in self.results['failed']:
                logger.error(f"  ✗ {check}")
            logger.info("")

        if self.results['warnings']:
            logger.warning("Warnings:")
            for warning in self.results['warnings']:
                logger.warning(f"  ⚠ {warning}")
            logger.info("")

        if failed_count == 0:
            logger.info("🎉 ALL CHECKS PASSED!")
        else:
            logger.error(f"❌ {failed_count} CHECK(S) FAILED")

        logger.info("=" * 80)

    def cleanup(self):
        """Clean up temporary test database."""
        if self.test_db_path.exists():
            try:
                self.test_db_path.unlink()
                logger.info(f"Cleaned up test database: {self.test_db_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up test database: {e}")


def main():
    """Main entry point."""
    verifier = MigrationVerifier(MIGRATIONS_DIR, TEST_DB_PATH)
    success = verifier.run_all_checks()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
