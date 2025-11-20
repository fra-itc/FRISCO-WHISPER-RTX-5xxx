# Quick Start Guide - TranscriptionService

## Installation

Ensure all dependencies are installed:

```bash
pip install -r requirements.txt
```

## 1. Simple One-Line Transcription

The fastest way to transcribe a file:

```python
from src.core.transcription_service import transcribe_file

result = transcribe_file(
    file_path='audio/meeting.mp3',
    model_size='large-v3',
    language='it'
)

print(f"Job ID: {result['job_id']}")
print(f"Transcript saved to: {result['output_path']}")
print(f"Language: {result['language']} ({result['language_probability']:.1%})")
print(f"Segments: {result['segments_count']}")
```

## 2. Using the Service Class

For more control and better resource management:

```python
from src.core import TranscriptionService

# Create service instance
with TranscriptionService(model_size='large-v3') as service:
    # Transcribe file
    result = service.transcribe_file(
        file_path='audio/meeting.mp3',
        language='it'
    )

    # Get job status
    job = service.get_job_status(result['job_id'])
    print(f"Status: {job['status']}")

    # Export to different formats
    service.export_transcript(
        transcript_id=result['transcript_id'],
        format_name='vtt',
        output_path='output/transcript.vtt'
    )
```

## 3. With Progress Monitoring

Track transcription progress in real-time:

```python
from src.core import TranscriptionService

def progress_handler(data):
    stage = data.get('stage')

    if stage == 'conversion':
        print(f"Converting: {data['progress_pct']:.1f}%")

    elif stage == 'transcription':
        if 'segment_number' in data:
            seg_num = data['segment_number']
            text = data['text'][:50]
            progress = data['progress_pct']
            print(f"[{seg_num:03d}] {progress:.1f}% - {text}...")

with TranscriptionService() as service:
    result = service.transcribe_file(
        file_path='audio/meeting.mp3',
        language='it',
        progress_callback=progress_handler
    )
```

## 4. Batch Processing

Process multiple files efficiently:

```python
from src.core import TranscriptionService

files = ['audio/file1.mp3', 'audio/file2.wav', 'audio/file3.m4a']

def batch_progress(idx, total, result):
    print(f"[{idx}/{total}] Completed: {result.get('output_path', 'N/A')}")

with TranscriptionService(model_size='medium') as service:
    results = service.transcribe_batch(
        file_paths=files,
        batch_progress_callback=batch_progress,
        language='it'
    )

    successful = sum(1 for r in results if r['success'])
    print(f"\nBatch complete: {successful}/{len(files)} successful")
```

## 5. Error Handling

Proper error handling:

```python
from src.core import TranscriptionService, TranscriptionServiceError

with TranscriptionService() as service:
    try:
        result = service.transcribe_file('audio/meeting.mp3', language='it')

        if result['success']:
            print(f"✓ Success! Job ID: {result['job_id']}")
        else:
            print(f"✗ Failed: {result.get('error')}")

    except TranscriptionServiceError as e:
        print(f"Service error: {e}")

    except FileNotFoundError as e:
        print(f"File error: {e}")
```

## 6. Custom Configuration

Configure the service for specific needs:

```python
from src.core import TranscriptionService

service = TranscriptionService(
    db_path='database/custom.db',      # Custom database location
    model_size='small',                  # Faster, smaller model
    device='cuda',                       # Force GPU usage
    compute_type='float16'               # Specific compute type
)

with service:
    result = service.transcribe_file(
        file_path='audio/meeting.mp3',
        language='it',
        beam_size=3,                     # Faster beam size
        vad_filter=True,                 # Voice Activity Detection
        word_timestamps=True,            # Word-level timestamps
        output_dir='output/custom'       # Custom output directory
    )
```

## 7. Working with Transcripts

Access and export transcripts:

```python
from src.core import TranscriptionService

with TranscriptionService() as service:
    # Transcribe
    result = service.transcribe_file('audio/meeting.mp3', language='it')
    transcript_id = result['transcript_id']

    # Get transcript with segments
    transcript = service.get_transcript(transcript_id)
    print(f"Full text: {transcript['text'][:100]}...")
    print(f"Segments: {len(transcript['segments'])}")

    # Export to multiple formats
    formats = ['srt', 'vtt', 'json', 'txt', 'csv']
    for fmt in formats:
        service.export_transcript(
            transcript_id=transcript_id,
            format_name=fmt,
            output_path=f'output/transcript.{fmt}'
        )
        print(f"✓ Exported to {fmt}")
```

## 8. System Statistics

Monitor system performance:

```python
from src.core import TranscriptionService

with TranscriptionService() as service:
    stats = service.get_statistics()

    print("\nDatabase:")
    print(f"  Total jobs: {stats['database']['total_jobs']}")
    print(f"  Completed: {stats['database']['completed_jobs']}")

    print("\nStorage:")
    print(f"  Total files: {stats['storage']['total_files']}")
    print(f"  Total size: {stats['storage']['total_size_formatted']}")
    print(f"  Quota used: {stats['storage']['quota_used_percentage']:.1f}%")

    print("\nTranscripts:")
    print(f"  Total: {stats['transcripts']['total_transcripts']}")
    print(f"  Versions: {stats['transcripts']['total_versions']}")
```

## 9. File Deduplication

Automatic duplicate detection:

```python
from src.core import TranscriptionService

with TranscriptionService() as service:
    # Transcribe same file twice
    result1 = service.transcribe_file('audio/meeting.mp3')
    result2 = service.transcribe_file('audio/meeting.mp3')

    # Check if duplicate was detected
    if result1['file_id'] == result2['file_id']:
        print("✓ Duplicate detected - same file used")
        print(f"  First: was_duplicate={result1['was_duplicate']}")
        print(f"  Second: was_duplicate={result2['was_duplicate']}")
```

## 10. Complete Example

Full-featured transcription workflow:

```python
from src.core import TranscriptionService, TranscriptionServiceError

def main():
    # Configuration
    audio_file = 'audio/meeting.mp3'
    model_size = 'large-v3'
    language = 'it'

    # Progress callback
    def progress(data):
        stage = data.get('stage', 'unknown')
        if stage == 'transcription' and 'segment_number' in data:
            print(f"Segment {data['segment_number']}: {data['progress_pct']:.1f}%")

    # Create service
    with TranscriptionService(model_size=model_size) as service:
        try:
            print(f"Transcribing: {audio_file}")
            print(f"Model: {model_size}, Language: {language}\n")

            # Transcribe
            result = service.transcribe_file(
                file_path=audio_file,
                language=language,
                progress_callback=progress
            )

            # Check success
            if not result['success']:
                print(f"Transcription failed: {result.get('error')}")
                return

            # Print results
            print(f"\n{'='*60}")
            print("TRANSCRIPTION COMPLETED")
            print(f"{'='*60}")
            print(f"Job ID: {result['job_id']}")
            print(f"File ID: {result['file_id']}")
            print(f"Transcript ID: {result['transcript_id']}")
            print(f"Output file: {result['output_path']}")
            print(f"Language: {result['language']} ({result['language_probability']:.1%})")
            print(f"Segments: {result['segments_count']}")
            print(f"Duration: {result['duration_seconds']:.2f}s")
            print(f"Processing time: {result['processing_time_seconds']:.2f}s")
            print(f"Device: {result['device']} ({result['compute_type']})")

            # Export to additional formats
            print(f"\nExporting to additional formats...")
            transcript_id = result['transcript_id']

            formats = {
                'vtt': 'output/transcript.vtt',
                'json': 'output/transcript.json',
                'txt': 'output/transcript.txt'
            }

            for fmt, path in formats.items():
                service.export_transcript(
                    transcript_id=transcript_id,
                    format_name=fmt,
                    output_path=path
                )
                print(f"  ✓ {fmt.upper()}: {path}")

            # Get job details
            job = service.get_job_status(result['job_id'])
            print(f"\nJob Status: {job['status']}")
            print(f"Created: {job['created_at']}")
            print(f"Completed: {job['completed_at']}")

        except TranscriptionServiceError as e:
            print(f"Error: {e}")
            return 1

    return 0

if __name__ == '__main__':
    exit(main())
```

## Tips

1. **Always use context managers** (`with` statements) for automatic cleanup
2. **Handle errors** with try-except blocks
3. **Monitor progress** for long files using callbacks
4. **Use batch processing** for multiple files
5. **Export formats** early to avoid reprocessing
6. **Check statistics** regularly to monitor system health
7. **Let deduplication work** - don't skip it unless needed

## Common Issues

### Issue: "Model not found"
**Solution**: First run will download the model. Ensure internet connection.

### Issue: "CUDA out of memory"
**Solution**: Use smaller model size or call `service.cleanup_resources()` between files.

### Issue: "File not found"
**Solution**: Use absolute paths or ensure working directory is correct.

### Issue: "Database locked"
**Solution**: Don't create multiple service instances simultaneously.

## Next Steps

- See [Integration Service Documentation](INTEGRATION_SERVICE.md) for detailed API reference
- Check [examples/integrated_transcription.py](../examples/integrated_transcription.py) for more examples
- Review [tests/integration/](../tests/integration/) for test cases
- Read [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for database structure

## Support

For issues or questions:
1. Check the documentation
2. Review example code
3. Run tests to verify setup
4. Check logs for detailed error messages
