#!/usr/bin/env python3
"""
Convenience script for running tests with common configurations.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py --fast       # Run only fast tests
    python run_tests.py --unit       # Run only unit tests
    python run_tests.py --coverage   # Run with HTML coverage report
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd):
    """Run a command and return the exit code."""
    print(f"Running: {' '.join(cmd)}")
    print("-" * 70)
    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Run tests with common configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_tests.py                    # All tests
    python run_tests.py --fast             # Fast tests only
    python run_tests.py --unit             # Unit tests only
    python run_tests.py --integration      # Integration tests only
    python run_tests.py --coverage         # With HTML coverage
    python run_tests.py --parallel         # Parallel execution
    python run_tests.py --file tests/unit/test_transcription.py
        """
    )

    parser.add_argument(
        '--fast',
        action='store_true',
        help='Run only fast tests (< 1 second)'
    )

    parser.add_argument(
        '--slow',
        action='store_true',
        help='Run only slow tests'
    )

    parser.add_argument(
        '--unit',
        action='store_true',
        help='Run only unit tests'
    )

    parser.add_argument(
        '--integration',
        action='store_true',
        help='Run only integration tests'
    )

    parser.add_argument(
        '--gpu',
        action='store_true',
        help='Run only GPU tests'
    )

    parser.add_argument(
        '--no-gpu',
        action='store_true',
        help='Skip GPU tests'
    )

    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Generate HTML coverage report'
    )

    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Run tests in parallel'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output'
    )

    parser.add_argument(
        '--file',
        type=str,
        help='Run specific test file'
    )

    parser.add_argument(
        '--pattern',
        '-k',
        type=str,
        help='Run tests matching pattern'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available tests without running'
    )

    args = parser.parse_args()

    # Build pytest command
    cmd = [sys.executable, '-m', 'pytest']

    # Add markers
    markers = []
    if args.fast:
        markers.append('fast')
    if args.slow:
        markers.append('slow')
    if args.unit:
        markers.append('unit')
    if args.integration:
        markers.append('integration')
    if args.gpu:
        markers.append('gpu')
    if args.no_gpu:
        markers.append('not gpu')

    if markers:
        cmd.extend(['-m', ' and '.join(markers)])

    # Add coverage
    if args.coverage:
        cmd.extend([
            '--cov=.',
            '--cov-report=html',
            '--cov-report=term'
        ])

    # Add parallel
    if args.parallel:
        cmd.extend(['-n', 'auto'])

    # Add verbosity
    if args.verbose:
        cmd.append('-vv')

    # Add file
    if args.file:
        cmd.append(args.file)

    # Add pattern
    if args.pattern:
        cmd.extend(['-k', args.pattern])

    # List tests
    if args.list:
        cmd.append('--collect-only')

    # Run the command
    exit_code = run_command(cmd)

    # Open coverage report if generated
    if args.coverage and exit_code == 0:
        coverage_file = Path('htmlcov/index.html')
        if coverage_file.exists():
            print("\n" + "=" * 70)
            print("Coverage report generated!")
            print(f"Open: {coverage_file.absolute()}")
            print("=" * 70)

            # Try to open automatically
            try:
                import webbrowser
                webbrowser.open(str(coverage_file.absolute()))
                print("Coverage report opened in browser.")
            except Exception:
                pass

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
