#!/usr/bin/env python3
"""
Run performance benchmarks for FRISCO WHISPER RTX 5xxx
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Now import and run benchmarks
from tests.performance.benchmark_suite import BenchmarkSuite

if __name__ == '__main__':
    suite = BenchmarkSuite()

    try:
        suite.run_all_benchmarks()
        suite.export_results('benchmark_results.json')
    finally:
        suite.cleanup()
