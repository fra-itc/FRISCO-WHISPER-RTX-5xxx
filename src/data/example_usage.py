#!/usr/bin/env python3
"""
Example Usage: DatabaseManager for FRISCO WHISPER RTX 5xxx
Demonstrates all major features of the database layer
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data import DatabaseManager, DatabaseError


def example_basic_usage():
    """Example 1: Basic job creation and management"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Job Creation and Management")
    print("="*70 + "\n")

    # Initialize database
    db = DatabaseManager('database/transcription.db')

    # Create a transcription job
    job_id = db.create_job(
        file_path='audio/example.m4a',
        model_size='medium',
        task_type='transcribe',
        language='en',
        compute_type='float16',
        device='cuda',
        beam_size=5,
        duration_seconds=120.5
    )
    print(f"✓ Job created: {job_id}")

    # Update job status to processing
    db.update_job(
        job_id=job_id,
        status='processing',
        started_at=datetime.now()
    )
    print(f"✓ Job status updated to 'processing'")

    # Get job details
    job = db.get_job(job_id)
    print(f"\nJob Details:")
    print(f"  Status: {job['status']}")
    print(f"  Model: {job['model_size']}")
    print(f"  File: {job['file_name']}")

    # Update job as completed
    db.update_job(
        job_id=job_id,
        status='completed',
        completed_at=datetime.now(),
        detected_language='en',
        language_probability=0.98,
        processing_time_seconds=15.3
    )
    print(f"\n✓ Job completed")

    db.close()


def example_transcription_save():
    """Example 2: Saving transcription results"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Saving Transcription Results")
    print("="*70 + "\n")

    db = DatabaseManager('database/transcription.db')

    # Create a job first
    job_id = db.create_job(
        file_path='audio/sample.mp3',
        model_size='large-v3',
        task_type='transcribe'
    )
    print(f"✓ Job created: {job_id}")

    # Update to completed
    db.update_job(job_id=job_id, status='completed')

    # Prepare transcription data
    segments = [
        {
            'id': 1,
            'start': 0.0,
            'end': 3.5,
            'text': 'Hello, this is a test transcription.'
        },
        {
            'id': 2,
            'start': 3.5,
            'end': 7.2,
            'text': 'The audio quality is excellent.'
        },
        {
            'id': 3,
            'start': 7.2,
            'end': 12.0,
            'text': 'Whisper AI produces accurate results.'
        }
    ]

    full_text = ' '.join([seg['text'] for seg in segments])

    # Save transcription
    transcription_id = db.save_transcription(
        job_id=job_id,
        text=full_text,
        language='en',
        segments=segments,
        srt_path='transcripts/sample.srt'
    )
    print(f"✓ Transcription saved: ID={transcription_id}")

    # Retrieve transcriptions
    transcriptions = db.get_transcriptions(job_id)
    print(f"\nTranscription Retrieved:")
    print(f"  Segments: {transcriptions[0]['segment_count']}")
    print(f"  Language: {transcriptions[0]['language']}")
    print(f"  First segment: {transcriptions[0]['segments'][0]['text']}")

    db.close()


def example_duplicate_detection():
    """Example 3: Duplicate file detection via hash"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Duplicate File Detection")
    print("="*70 + "\n")

    db = DatabaseManager('database/transcription.db')

    # First job with a file
    file_path = 'audio/example.m4a'
    job_id_1 = db.create_job(
        file_path=file_path,
        model_size='medium'
    )
    print(f"✓ First job created: {job_id_1}")

    # Try to create another job with same file
    job_id_2 = db.create_job(
        file_path=file_path,
        model_size='large-v3'  # Different model, same file
    )
    print(f"✓ Second job created: {job_id_2}")

    # Check that both jobs reference the same file_id
    job1 = db.get_job(job_id_1)
    job2 = db.get_job(job_id_2)

    if job1['file_id'] == job2['file_id']:
        print(f"\n✓ Duplicate detection working! Both jobs share file_id={job1['file_id']}")
        print(f"  File hash: {job1['file_hash'][:16]}...")
    else:
        print("\n✗ Error: Duplicate detection not working")

    db.close()


def example_full_text_search():
    """Example 4: Full-text search in transcriptions"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Full-Text Search")
    print("="*70 + "\n")

    db = DatabaseManager('database/transcription.db')

    # Create jobs with transcriptions
    jobs_data = [
        {
            'file': 'audio/interview.mp3',
            'text': 'This is an interview about artificial intelligence and machine learning.',
            'language': 'en'
        },
        {
            'file': 'audio/lecture.mp3',
            'text': 'Today we will discuss quantum computing and its applications.',
            'language': 'en'
        },
        {
            'file': 'audio/podcast.mp3',
            'text': 'Welcome to the podcast about artificial neural networks.',
            'language': 'en'
        }
    ]

    for data in jobs_data:
        job_id = db.create_job(file_path=data['file'], model_size='medium')
        db.update_job(job_id=job_id, status='completed')
        db.save_transcription(
            job_id=job_id,
            text=data['text'],
            language=data['language'],
            segments=[{'id': 1, 'start': 0.0, 'end': 5.0, 'text': data['text']}]
        )

    print(f"✓ Created {len(jobs_data)} jobs with transcriptions")

    # Search for "artificial"
    results = db.search_transcriptions(query='artificial', limit=10)
    print(f"\nSearch Results for 'artificial': {len(results)} matches")
    for i, result in enumerate(results, 1):
        print(f"\n  [{i}] Job ID: {result['job_id'][:8]}...")
        print(f"      Text: {result['text'][:80]}...")
        if 'snippet' in result:
            print(f"      Snippet: {result['snippet']}")

    db.close()


def example_statistics():
    """Example 5: Database statistics"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Database Statistics")
    print("="*70 + "\n")

    db = DatabaseManager('database/transcription.db')

    stats = db.get_statistics()

    print("Database Statistics:")
    print(f"  Total Jobs: {stats['total_jobs']}")
    print(f"  Completed: {stats['completed_jobs']}")
    print(f"  Failed: {stats['failed_jobs']}")
    print(f"  Processing: {stats['processing_jobs']}")
    print(f"  Pending: {stats['pending_jobs']}")
    print(f"  Unique Files: {stats['unique_files']}")

    if stats['avg_processing_time']:
        print(f"  Avg Processing Time: {stats['avg_processing_time']:.2f}s")

    if stats['total_audio_duration']:
        print(f"  Total Audio Duration: {stats['total_audio_duration']:.1f}s")

    if stats['total_size']:
        print(f"  Total File Size: {stats['total_size'] / (1024*1024):.2f} MB")

    db.close()


def example_query_jobs():
    """Example 6: Querying jobs by status"""
    print("\n" + "="*70)
    print("EXAMPLE 6: Query Jobs by Status")
    print("="*70 + "\n")

    db = DatabaseManager('database/transcription.db')

    # Get recent jobs
    recent = db.get_recent_jobs(limit=10)
    print(f"Recent Jobs: {len(recent)}")
    for job in recent[:3]:
        print(f"  - {job['file_name']} ({job['status']}) - {job['model_size']}")

    # Get jobs by status
    completed = db.get_jobs_by_status('completed', limit=5)
    print(f"\nCompleted Jobs: {len(completed)}")

    pending = db.get_jobs_by_status('pending', limit=5)
    print(f"Pending Jobs: {len(pending)}")

    db.close()


def example_transaction():
    """Example 7: Using transactions for atomic operations"""
    print("\n" + "="*70)
    print("EXAMPLE 7: Atomic Transactions")
    print("="*70 + "\n")

    db = DatabaseManager('database/transcription.db')

    try:
        with db.transaction():
            # Create multiple jobs atomically
            job_id_1 = db.create_job(
                file_path='audio/file1.mp3',
                model_size='medium'
            )
            job_id_2 = db.create_job(
                file_path='audio/file2.mp3',
                model_size='medium'
            )

            print(f"✓ Transaction successful: created jobs {job_id_1[:8]}... and {job_id_2[:8]}...")

    except DatabaseError as e:
        print(f"✗ Transaction failed: {e}")

    db.close()


def example_context_manager():
    """Example 8: Using DatabaseManager as context manager"""
    print("\n" + "="*70)
    print("EXAMPLE 8: Context Manager Usage")
    print("="*70 + "\n")

    # Database will automatically close when exiting context
    with DatabaseManager('database/transcription.db') as db:
        job_id = db.create_job(
            file_path='audio/context_test.mp3',
            model_size='small'
        )
        print(f"✓ Job created with context manager: {job_id}")

        job = db.get_job(job_id)
        print(f"✓ Job status: {job['status']}")

    print("✓ Database connection automatically closed")


def example_error_handling():
    """Example 9: Error handling"""
    print("\n" + "="*70)
    print("EXAMPLE 9: Error Handling")
    print("="*70 + "\n")

    db = DatabaseManager('database/transcription.db')

    # Try to get non-existent job
    job = db.get_job('non-existent-uuid')
    print(f"Non-existent job result: {job}")  # Should be None

    # Try to create job with non-existent file
    try:
        job_id = db.create_job(
            file_path='audio/non_existent_file.mp3',
            model_size='medium'
        )
    except DatabaseError as e:
        print(f"✓ Error caught: {e}")

    # Try to update non-existent job
    success = db.update_job('fake-uuid', status='completed')
    print(f"Update non-existent job: {success}")  # Should be False

    db.close()


def example_cleanup():
    """Example 10: Cleanup old jobs"""
    print("\n" + "="*70)
    print("EXAMPLE 10: Cleanup Old Jobs")
    print("="*70 + "\n")

    db = DatabaseManager('database/transcription.db')

    # Cleanup completed jobs older than 30 days
    deleted = db.cleanup_old_jobs(days=30, status='completed')
    print(f"✓ Cleaned up {deleted} old completed jobs")

    # Cleanup failed jobs older than 7 days
    deleted = db.cleanup_old_jobs(days=7, status='failed')
    print(f"✓ Cleaned up {deleted} old failed jobs")

    db.close()


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("  FRISCO WHISPER RTX 5xxx - Database Layer Examples")
    print("="*70)

    examples = [
        ("Basic Usage", example_basic_usage),
        ("Transcription Save", example_transcription_save),
        ("Duplicate Detection", example_duplicate_detection),
        ("Full-Text Search", example_full_text_search),
        ("Statistics", example_statistics),
        ("Query Jobs", example_query_jobs),
        ("Transactions", example_transaction),
        ("Context Manager", example_context_manager),
        ("Error Handling", example_error_handling),
        ("Cleanup", example_cleanup),
    ]

    print("\nAvailable Examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  [{i}] {name}")
    print(f"  [0] Run All Examples")

    choice = input("\nSelect example [0-10]: ").strip()

    if choice == '0':
        for name, func in examples:
            try:
                func()
            except Exception as e:
                print(f"\n✗ Error in {name}: {e}")
    elif choice.isdigit() and 1 <= int(choice) <= len(examples):
        try:
            examples[int(choice) - 1][1]()
        except Exception as e:
            print(f"\n✗ Error: {e}")
    else:
        print("Invalid choice!")

    print("\n" + "="*70)
    print("Examples completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
