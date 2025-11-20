#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - Integration Verification Script
Quick verification that all components are properly integrated
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_imports():
    """Test that all modules can be imported."""
    print("\n" + "="*80)
    print("TEST 1: Module Imports")
    print("="*80)

    try:
        # Core imports
        from src.core import TranscriptionEngine, TranscriptionService
        print("[OK] Core modules imported successfully")

        # Data layer imports
        from src.data import DatabaseManager, FileManager, TranscriptManager
        print("[OK] Data layer modules imported successfully")

        # Check TranscriptionService is available
        assert hasattr(TranscriptionService, 'transcribe_file')
        assert hasattr(TranscriptionService, 'transcribe_batch')
        print("[OK] TranscriptionService methods available")

        return True

    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        return False


def test_service_initialization():
    """Test service can be initialized."""
    print("\n" + "="*80)
    print("TEST 2: Service Initialization")
    print("="*80)

    try:
        from src.core import TranscriptionService

        # Create service with test database
        service = TranscriptionService(
            db_path='database/integration_test.db',
            model_size='tiny'
        )

        print(f"[OK] Service created: {service}")

        # Check components are initialized
        assert service.db is not None
        print("[OK] DatabaseManager initialized")

        assert service.file_manager is not None
        print("[OK] FileManager initialized")

        assert service.transcript_manager is not None
        print("[OK] TranscriptManager initialized")

        assert service.audio_processor is not None
        print("[OK] AudioProcessor initialized")

        # Clean up
        service.close()
        print("[OK] Service closed successfully")

        return True

    except Exception as e:
        print(f"[FAIL] Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_context_manager():
    """Test service as context manager."""
    print("\n" + "="*80)
    print("TEST 3: Context Manager")
    print("="*80)

    try:
        from src.core import TranscriptionService

        with TranscriptionService(db_path='database/integration_test.db') as service:
            assert service.db is not None
            print("[OK] Context manager entry successful")

        print("[OK] Context manager exit successful")

        return True

    except Exception as e:
        print(f"[FAIL] Context manager failed: {e}")
        return False


def test_convenience_function():
    """Test convenience function import."""
    print("\n" + "="*80)
    print("TEST 4: Convenience Function")
    print("="*80)

    try:
        from src.core.transcription_service import transcribe_file

        assert callable(transcribe_file)
        print("[OK] transcribe_file() function available")

        # Check function signature
        import inspect
        sig = inspect.signature(transcribe_file)
        params = list(sig.parameters.keys())

        expected_params = ['file_path', 'model_size', 'language', 'output_dir', 'db_path']
        for param in expected_params:
            assert param in params
            print(f"[OK] Parameter '{param}' present")

        return True

    except Exception as e:
        print(f"[FAIL] Convenience function failed: {e}")
        return False


def test_database_operations():
    """Test basic database operations."""
    print("\n" + "="*80)
    print("TEST 5: Database Operations")
    print("="*80)

    try:
        from src.core import TranscriptionService

        with TranscriptionService(db_path='database/integration_test.db') as service:
            # Test statistics
            stats = service.get_statistics()

            assert 'database' in stats
            print("[OK] Database statistics available")

            assert 'storage' in stats
            print("[OK] Storage statistics available")

            assert 'transcripts' in stats
            print("[OK] Transcript statistics available")

            # Test job queries
            recent_jobs = service.db.get_recent_jobs(limit=10)
            print(f"[OK] Retrieved recent jobs: {len(recent_jobs)} jobs")

        return True

    except Exception as e:
        print(f"[FAIL] Database operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_example_file():
    """Test that example file exists and is valid Python."""
    print("\n" + "="*80)
    print("TEST 6: Example File")
    print("="*80)

    try:
        example_file = Path(__file__).parent.parent.parent / 'examples' / 'integrated_transcription.py'

        assert example_file.exists()
        print(f"[OK] Example file exists: {example_file}")

        # Try to compile it
        with open(example_file, 'r') as f:
            code = f.read()

        compile(code, str(example_file), 'exec')
        print("[OK] Example file is valid Python")

        return True

    except Exception as e:
        print(f"[FAIL] Example file check failed: {e}")
        return False


def test_documentation():
    """Test that documentation files exist."""
    print("\n" + "="*80)
    print("TEST 7: Documentation")
    print("="*80)

    try:
        docs_dir = Path(__file__).parent.parent.parent / 'docs'

        docs = [
            'INTEGRATION_SERVICE.md',
            'QUICK_START_INTEGRATION.md'
        ]

        for doc in docs:
            doc_path = docs_dir / doc
            assert doc_path.exists()
            print(f"[OK] Documentation exists: {doc}")

        report = Path(__file__).parent.parent.parent / 'INTEGRATION_REPORT.md'
        assert report.exists()
        print(f"[OK] Report exists: {report.name}")

        return True

    except Exception as e:
        print(f"[FAIL] Documentation check failed: {e}")
        return False


def test_file_parsing():
    """Test SRT parsing utility."""
    print("\n" + "="*80)
    print("TEST 8: File Parsing Utilities")
    print("="*80)

    try:
        from src.core import TranscriptionService

        service = TranscriptionService(db_path='database/integration_test.db')

        # Test timestamp parsing
        timestamp_tests = [
            ('00:00:00,000', 0.0),
            ('00:00:05,000', 5.0),
            ('00:01:00,000', 60.0),
            ('01:00:00,000', 3600.0),
        ]

        for timestamp_str, expected in timestamp_tests:
            result = service._parse_srt_timestamp(timestamp_str)
            assert abs(result - expected) < 0.01
            print(f"[OK] Timestamp parsed: {timestamp_str} -> {result}s")

        service.close()

        return True

    except Exception as e:
        print(f"[FAIL] File parsing failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("\n" + "="*80)
    print("FRISCO WHISPER RTX 5xxx - Integration Verification")
    print("="*80)

    tests = [
        ("Module Imports", test_imports),
        ("Service Initialization", test_service_initialization),
        ("Context Manager", test_context_manager),
        ("Convenience Function", test_convenience_function),
        ("Database Operations", test_database_operations),
        ("Example File", test_example_file),
        ("Documentation", test_documentation),
        ("File Parsing", test_file_parsing),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[FAIL] Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"{status}: {name}")

    print("\n" + "="*80)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("="*80)

    if passed == total:
        print("\n[SUCCESS] All integration tests passed! Integration layer is ready.")
        return 0
    else:
        print(f"\n[WARNING]  {total - passed} test(s) failed. Review output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
