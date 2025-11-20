#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - Performance Benchmark Suite
Comprehensive performance testing and benchmarking
"""

import time
import tempfile
import shutil
import wave
import struct
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import threading

from src.data.database import DatabaseManager
from src.data.file_manager import FileManager
from src.data.transcript_manager import TranscriptManager


class BenchmarkResult:
    """Store benchmark results."""

    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.end_time = None
        self.duration = None
        self.operations = 0
        self.throughput = 0.0
        self.metadata = {}

    def start(self):
        """Start timing."""
        self.start_time = time.time()

    def stop(self, operations: int = 1):
        """Stop timing and calculate metrics."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.operations = operations
        self.throughput = operations / self.duration if self.duration > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'duration_seconds': round(self.duration, 3) if self.duration else None,
            'operations': self.operations,
            'throughput_ops_per_sec': round(self.throughput, 2),
            'metadata': self.metadata
        }


class BenchmarkSuite:
    """
    Performance benchmark suite for Frisco Whisper system.

    Tests:
    - Batch upload performance
    - Concurrent transcription handling
    - Database query performance
    - Search performance
    - Export performance
    """

    def __init__(self):
        """Initialize benchmark environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix='frisco_benchmark_'))
        self.db_path = self.test_dir / 'benchmark.db'
        self.upload_dir = self.test_dir / 'uploads'
        self.transcripts_dir = self.test_dir / 'transcripts'

        for d in [self.upload_dir, self.transcripts_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.db = DatabaseManager(str(self.db_path))
        self.file_mgr = FileManager(self.db, base_dir=self.upload_dir)
        self.transcript_mgr = TranscriptManager(self.db)

        self.results: List[BenchmarkResult] = []

    def cleanup(self):
        """Cleanup test environment."""
        self.db.close()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def create_sample_audio(self, name: str, duration: float = 1.0) -> Path:
        """Create sample WAV file."""
        audio_file = self.test_dir / name

        sample_rate = 16000
        num_samples = int(sample_rate * duration)

        with wave.open(str(audio_file), 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)

            for i in range(num_samples):
                value = int(32767 * 0.1 * (i % 100) / 100)
                wav_file.writeframes(struct.pack('<h', value))

        return audio_file

    def benchmark_batch_uploads(self, count: int = 100):
        """Benchmark batch file uploads."""
        result = BenchmarkResult(f'Batch Upload ({count} files)')
        result.start()

        # Create sample files
        files = []
        for i in range(count):
            audio_file = self.create_sample_audio(f'batch_{i}.wav', duration=0.5)
            files.append(audio_file)

        # Upload all files
        for file in files:
            self.file_mgr.upload_file(str(file))

        result.stop(operations=count)
        result.metadata = {
            'files_uploaded': count,
            'avg_time_per_file_ms': round((result.duration / count) * 1000, 2)
        }

        self.results.append(result)
        return result

    def benchmark_job_creation(self, count: int = 1000):
        """Benchmark job creation performance."""
        result = BenchmarkResult(f'Job Creation ({count} jobs)')

        # Create one sample file
        audio_file = self.create_sample_audio('job_test.wav')

        result.start()

        for i in range(count):
            self.db.create_job(
                file_path=str(audio_file),
                model_size='base',
                task_type='transcribe',
                language='en'
            )

        result.stop(operations=count)
        result.metadata = {
            'jobs_created': count,
            'avg_time_per_job_ms': round((result.duration / count) * 1000, 3)
        }

        self.results.append(result)
        return result

    def benchmark_transcript_save(self, count: int = 100):
        """Benchmark transcript save performance."""
        result = BenchmarkResult(f'Transcript Save ({count} transcripts)')

        # Create jobs
        audio_file = self.create_sample_audio('transcript_test.wav')
        job_ids = []

        for i in range(count):
            job_id = self.db.create_job(
                file_path=str(audio_file),
                model_size='base',
                task_type='transcribe'
            )
            job_ids.append(job_id)

        # Benchmark saving transcripts
        result.start()

        segments = [
            {'start': 0.0, 'end': 1.0, 'text': f'Test segment {i}'}
            for i in range(10)
        ]

        for i, job_id in enumerate(job_ids):
            self.transcript_mgr.save_transcript(
                job_id=job_id,
                text=f'Test transcript {i}',
                segments=segments,
                language='en'
            )

        result.stop(operations=count)
        result.metadata = {
            'transcripts_saved': count,
            'segments_per_transcript': len(segments),
            'avg_time_per_transcript_ms': round((result.duration / count) * 1000, 2)
        }

        self.results.append(result)
        return result

    def benchmark_search_performance(self, corpus_size: int = 1000, searches: int = 100):
        """Benchmark full-text search performance."""
        result = BenchmarkResult(f'Search Performance ({searches} searches on {corpus_size} docs)')

        # Create corpus
        audio_file = self.create_sample_audio('search_test.wav')

        search_terms = ['apple', 'banana', 'cherry', 'date', 'elderberry']

        for i in range(corpus_size):
            job_id = self.db.create_job(
                file_path=str(audio_file),
                model_size='base',
                task_type='transcribe'
            )

            # Include search terms in some transcripts
            text = f"Document {i} contains {search_terms[i % len(search_terms)]}"
            segments = [{'start': 0.0, 'end': 1.0, 'text': text}]

            self.transcript_mgr.save_transcript(
                job_id=job_id,
                text=text,
                segments=segments,
                language='en'
            )

        # Benchmark searches
        result.start()

        total_results = 0
        for i in range(searches):
            term = search_terms[i % len(search_terms)]
            results = self.db.search_transcriptions(term)
            total_results += len(results)

        result.stop(operations=searches)
        result.metadata = {
            'corpus_size': corpus_size,
            'searches_performed': searches,
            'avg_results_per_search': round(total_results / searches, 1),
            'avg_search_time_ms': round((result.duration / searches) * 1000, 2)
        }

        self.results.append(result)
        return result

    def benchmark_concurrent_operations(self, threads: int = 5, ops_per_thread: int = 20):
        """Benchmark concurrent database operations."""
        result = BenchmarkResult(f'Concurrent Operations ({threads} threads, {ops_per_thread} ops each)')

        audio_file = self.create_sample_audio('concurrent_test.wav')

        completed = {'count': 0}
        lock = threading.Lock()

        def worker(thread_id: int):
            for i in range(ops_per_thread):
                job_id = self.db.create_job(
                    file_path=str(audio_file),
                    model_size='base',
                    task_type='transcribe'
                )

                text = f'Thread {thread_id} operation {i}'
                segments = [{'start': 0.0, 'end': 1.0, 'text': text}]

                self.transcript_mgr.save_transcript(
                    job_id=job_id,
                    text=text,
                    segments=segments,
                    language='en'
                )

                with lock:
                    completed['count'] += 1

        result.start()

        # Create and start threads
        thread_list = []
        for i in range(threads):
            t = threading.Thread(target=worker, args=(i,))
            thread_list.append(t)
            t.start()

        # Wait for completion
        for t in thread_list:
            t.join()

        result.stop(operations=threads * ops_per_thread)
        result.metadata = {
            'threads': threads,
            'operations_per_thread': ops_per_thread,
            'total_operations': completed['count'],
            'avg_time_per_operation_ms': round((result.duration / completed['count']) * 1000, 2)
        }

        self.results.append(result)
        return result

    def benchmark_version_operations(self, transcripts: int = 50, versions_per: int = 10):
        """Benchmark version creation and retrieval."""
        result = BenchmarkResult(f'Version Operations ({transcripts} transcripts × {versions_per} versions)')

        audio_file = self.create_sample_audio('version_test.wav')

        # Create transcripts
        transcript_ids = []
        for i in range(transcripts):
            job_id = self.db.create_job(
                file_path=str(audio_file),
                model_size='base',
                task_type='transcribe'
            )

            segments = [{'start': 0.0, 'end': 1.0, 'text': f'Original {i}'}]
            transcript_id = self.transcript_mgr.save_transcript(
                job_id=job_id,
                text=f'Original {i}',
                segments=segments,
                language='en'
            )
            transcript_ids.append(transcript_id)

        # Benchmark version creation
        result.start()

        for transcript_id in transcript_ids:
            for v in range(versions_per - 1):  # -1 because initial is version 1
                segments = [{'start': 0.0, 'end': 1.0, 'text': f'Version {v+2}'}]
                self.transcript_mgr.update_transcript(
                    transcript_id=transcript_id,
                    text=f'Version {v+2}',
                    segments=segments,
                    change_note=f'Update {v+2}'
                )

        result.stop(operations=transcripts * versions_per)
        result.metadata = {
            'transcripts': transcripts,
            'versions_per_transcript': versions_per,
            'total_versions_created': transcripts * versions_per,
            'avg_time_per_version_ms': round((result.duration / (transcripts * versions_per)) * 1000, 2)
        }

        self.results.append(result)
        return result

    def benchmark_export_performance(self, transcripts: int = 50, formats: int = 5):
        """Benchmark export to multiple formats."""
        result = BenchmarkResult(f'Export Performance ({transcripts} transcripts × {formats} formats)')

        audio_file = self.create_sample_audio('export_test.wav')
        export_formats = ['srt', 'vtt', 'json', 'txt', 'csv'][:formats]

        # Create transcripts
        transcript_ids = []
        for i in range(transcripts):
            job_id = self.db.create_job(
                file_path=str(audio_file),
                model_size='base',
                task_type='transcribe'
            )

            segments = [
                {'start': j * 2.0, 'end': (j + 1) * 2.0, 'text': f'Segment {j}'}
                for j in range(5)
            ]

            text = ' '.join([s['text'] for s in segments])
            transcript_id = self.transcript_mgr.save_transcript(
                job_id=job_id,
                text=text,
                segments=segments,
                language='en'
            )
            transcript_ids.append(transcript_id)

        # Benchmark exports
        result.start()

        total_exports = 0
        for transcript_id in transcript_ids:
            for format_name in export_formats:
                output_path = self.transcripts_dir / f'export_{transcript_id}.{format_name}'
                self.transcript_mgr.export_transcript(
                    transcript_id=transcript_id,
                    format_name=format_name,
                    output_path=str(output_path)
                )
                total_exports += 1

        result.stop(operations=total_exports)
        result.metadata = {
            'transcripts': transcripts,
            'formats': formats,
            'total_exports': total_exports,
            'avg_time_per_export_ms': round((result.duration / total_exports) * 1000, 2)
        }

        self.results.append(result)
        return result

    def run_all_benchmarks(self):
        """Run complete benchmark suite."""
        print("="*70)
        print("FRISCO WHISPER RTX 5xxx - Performance Benchmark Suite")
        print("="*70)
        print()

        benchmarks = [
            ('Batch Uploads', lambda: self.benchmark_batch_uploads(100)),
            ('Job Creation', lambda: self.benchmark_job_creation(1000)),
            ('Transcript Save', lambda: self.benchmark_transcript_save(100)),
            ('Search Performance', lambda: self.benchmark_search_performance(1000, 100)),
            ('Concurrent Operations', lambda: self.benchmark_concurrent_operations(5, 20)),
            ('Version Operations', lambda: self.benchmark_version_operations(50, 10)),
            ('Export Performance', lambda: self.benchmark_export_performance(50, 5))
        ]

        for name, benchmark_func in benchmarks:
            print(f"Running: {name}...")
            result = benchmark_func()
            print(f"  [OK] Completed in {result.duration:.2f}s ({result.throughput:.2f} ops/sec)")
            print()

        print("="*70)
        print("BENCHMARK RESULTS")
        print("="*70)
        print()

        for result in self.results:
            print(f"{result.name}:")
            print(f"  Duration: {result.duration:.3f}s")
            print(f"  Operations: {result.operations}")
            print(f"  Throughput: {result.throughput:.2f} ops/sec")
            if result.metadata:
                for key, value in result.metadata.items():
                    print(f"  {key}: {value}")
            print()

    def export_results(self, output_file: str = 'benchmark_results.json'):
        """Export results to JSON."""
        output_path = Path(output_file)

        results_data = {
            'timestamp': datetime.now().isoformat(),
            'system_info': {
                'database': str(self.db_path),
                'test_dir': str(self.test_dir)
            },
            'results': [r.to_dict() for r in self.results]
        }

        with open(output_path, 'w') as f:
            json.dump(results_data, f, indent=2)

        print(f"Results exported to: {output_path}")


def main():
    """Run benchmark suite."""
    suite = BenchmarkSuite()

    try:
        suite.run_all_benchmarks()
        suite.export_results('benchmark_results.json')
    finally:
        suite.cleanup()


if __name__ == '__main__':
    main()
