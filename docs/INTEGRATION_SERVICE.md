# TranscriptionService - Integration Layer Documentation

## Overview

The `TranscriptionService` is a high-level integration service that combines the `TranscriptionEngine` with the data layer components (`DatabaseManager`, `FileManager`, and `TranscriptManager`) to provide a complete transcription workflow.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   TranscriptionService                       │
│  High-level API for complete transcription workflows        │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────────┐   ┌──────────────┐
│ Transcription│    │   DatabaseManager │   │ FileManager  │
│    Engine    │    │  Job tracking &   │   │ Upload &     │
│  (Core AI)   │    │  status updates   │   │ dedup        │
└──────────────┘    └──────────────────┘   └──────────────┘
        │                     │                     │
        │                     ▼                     │
        │            ┌──────────────────┐           │
        │            │ TranscriptManager│           │
        │            │  Versioning &    │           │
        │            │  export          │           │
        │            └──────────────────┘           │
        │                                            │
        └────────────────────┬──────────────────────┘
                             │
                             ▼
                    ┌──────────────┐
                    │  Audio       │
                    │  Processor   │
                    │  Convert &   │
                    │  validate    │
                    └──────────────┘
```

## Key Features

### 1. Complete Workflow Integration
- File upload with deduplication
- Audio format conversion (when needed)
- Job creation and tracking
- Transcription execution
- Result storage with versioning
- Database updates

### 2. Job Management
- Automatic job creation in database
- Real-time status tracking (pending → processing → completed/failed)
- Error handling with proper rollback
- Processing time tracking

### 3. File Deduplication
- SHA256-based duplicate detection
- Automatic reuse of existing files
- Storage optimization

### 4. Progress Monitoring
- Stage-based progress updates (conversion, transcription)
- Segment-level progress callbacks
- Database integration for status updates

### 5. Batch Processing
- Process multiple files efficiently
- Per-file progress tracking
- Error isolation (one failure doesn't stop batch)

### 6. Export Integration
- Direct access to TranscriptManager export features
- Multiple format support (SRT, VTT, JSON, TXT, CSV)
- Version control

## API Reference

### Class: TranscriptionService

#### Constructor

```python
TranscriptionService(
    db_path: str = 'database/transcription.db',
    model_size: str = 'large-v3',
    device: Optional[str] = None,
    compute_type: Optional[str] = None
)
```

**Parameters:**
- `db_path`: Path to SQLite database file
- `model_size`: Default Whisper model size
- `device`: Device to use ('cuda' or 'cpu'), auto-detected if None
- `compute_type`: Compute type, auto-detected if None

#### Main Methods

##### transcribe_file()

Complete transcription workflow for a single file.

```python
result = service.transcribe_file(
    file_path: str,
    model_size: Optional[str] = None,
    task: str = 'transcribe',
    language: Optional[str] = None,
    beam_size: int = 5,
    vad_filter: bool = True,
    word_timestamps: bool = False,
    output_dir: Optional[str] = None,
    progress_callback: Optional[Callable] = None,
    skip_duplicate_check: bool = False
) -> Dict[str, Any]
```

**Returns:**
```python
{
    'success': True,
    'job_id': 'uuid-string',
    'file_id': 123,
    'transcript_id': 456,
    'output_path': '/path/to/output.srt',
    'segments_count': 42,
    'language': 'en',
    'language_probability': 0.95,
    'duration_seconds': 120.5,
    'processing_time_seconds': 45.2,
    'was_duplicate': False,
    'model_size': 'large-v3',
    'device': 'cuda',
    'compute_type': 'float16'
}
```

##### transcribe_batch()

Process multiple files in batch.

```python
results = service.transcribe_batch(
    file_paths: List[str],
    batch_progress_callback: Optional[Callable] = None,
    **transcription_options
) -> List[Dict[str, Any]]
```

**Batch Progress Callback:**
```python
def batch_progress_handler(file_index: int, total_files: int, result: dict):
    print(f"Completed {file_index}/{total_files}")
```

##### get_job_status()

Get current status of a transcription job.

```python
job_status = service.get_job_status(job_id: str) -> Optional[Dict[str, Any]]
```

##### get_transcript()

Get transcript with segments.

```python
transcript = service.get_transcript(
    transcript_id: int,
    version: Optional[int] = None
) -> Dict[str, Any]
```

##### export_transcript()

Export transcript to specified format.

```python
content = service.export_transcript(
    transcript_id: int,
    format_name: str,
    output_path: str,
    version: Optional[int] = None
) -> str
```

##### get_statistics()

Get comprehensive system statistics.

```python
stats = service.get_statistics() -> Dict[str, Any]
```

**Returns:**
```python
{
    'database': {
        'total_jobs': 100,
        'completed_jobs': 95,
        'failed_jobs': 3,
        'pending_jobs': 2
    },
    'storage': {
        'total_files': 50,
        'total_size_formatted': '1.5 GB',
        'quota_used_percentage': 15.0
    },
    'transcripts': {
        'total_transcripts': 95,
        'total_versions': 120,
        'total_exports': 200
    }
}
```

## Usage Examples

### 1. Basic Transcription

```python
from src.core import TranscriptionService

# Simple one-liner
from src.core.transcription_service import transcribe_file

result = transcribe_file(
    file_path='audio/meeting.mp3',
    model_size='large-v3',
    language='it'
)

print(f"Job ID: {result['job_id']}")
print(f"Output: {result['output_path']}")
```

### 2. With Progress Monitoring

```python
from src.core import TranscriptionService

def progress_handler(progress_data):
    stage = progress_data.get('stage', 'unknown')

    if stage == 'conversion':
        print(f"Converting: {progress_data['progress_pct']:.1f}%")
    elif stage == 'transcription':
        seg = progress_data.get('segment_number')
        if seg:
            print(f"Segment {seg}: {progress_data['text'][:50]}...")

with TranscriptionService(model_size='large-v3') as service:
    result = service.transcribe_file(
        file_path='audio/meeting.mp3',
        language='it',
        progress_callback=progress_handler
    )
```

### 3. Batch Processing

```python
from src.core import TranscriptionService

audio_files = [
    'audio/meeting1.mp3',
    'audio/meeting2.wav',
    'audio/interview.m4a'
]

def batch_progress(file_index, total_files, result):
    print(f"[{file_index}/{total_files}] {result['output_path']}")

with TranscriptionService() as service:
    results = service.transcribe_batch(
        file_paths=audio_files,
        batch_progress_callback=batch_progress,
        language='it'
    )

    successful = sum(1 for r in results if r['success'])
    print(f"Completed: {successful}/{len(results)}")
```

### 4. Export to Multiple Formats

```python
from src.core import TranscriptionService

with TranscriptionService() as service:
    result = service.transcribe_file('audio/meeting.mp3', language='it')

    transcript_id = result['transcript_id']

    # Export to different formats
    service.export_transcript(transcript_id, 'srt', 'output/transcript.srt')
    service.export_transcript(transcript_id, 'vtt', 'output/transcript.vtt')
    service.export_transcript(transcript_id, 'json', 'output/transcript.json')
    service.export_transcript(transcript_id, 'txt', 'output/transcript.txt')
```

### 5. Job Status Monitoring

```python
from src.core import TranscriptionService

with TranscriptionService() as service:
    result = service.transcribe_file('audio/meeting.mp3')

    job_id = result['job_id']
    job_status = service.get_job_status(job_id)

    print(f"Status: {job_status['status']}")
    print(f"Language: {job_status['detected_language']}")
    print(f"Processing time: {job_status['processing_time_seconds']:.2f}s")
```

### 6. Error Handling

```python
from src.core import TranscriptionService, TranscriptionServiceError

with TranscriptionService() as service:
    try:
        result = service.transcribe_file('audio/meeting.mp3')

        if result['success']:
            print(f"Success! Job ID: {result['job_id']}")
        else:
            print(f"Failed: {result.get('error')}")

    except TranscriptionServiceError as e:
        print(f"Service error: {e}")

        # Check if job was created
        jobs = service.db.get_recent_jobs(limit=1)
        if jobs and jobs[0]['status'] == 'failed':
            print(f"Job marked as failed: {jobs[0]['error_message']}")
```

## Workflow Stages

### Stage 1: File Preparation
1. Validate file exists
2. Get audio metadata (duration, format, sample rate)
3. Convert to WAV if needed (with progress callback)

### Stage 2: File Upload
1. Upload file to storage
2. Calculate SHA256 hash
3. Check for duplicates
4. Return file_id (existing or new)

### Stage 3: Job Creation
1. Create job in database
2. Set status to 'pending'
3. Store job parameters (model, language, etc.)
4. Return job_id

### Stage 4: Transcription
1. Update job status to 'processing'
2. Load transcription model (lazy loading)
3. Perform transcription with progress updates
4. Handle transcription errors

### Stage 5: Result Storage
1. Parse SRT output into segments
2. Save transcript to database (creates version 1)
3. Update job with results
4. Set job status to 'completed'

### Stage 6: Cleanup
1. Remove temporary files (if conversion was done)
2. Return complete result dictionary

## Error Handling

### Automatic Rollback
- Failed transcriptions automatically update job status to 'failed'
- Error messages stored in database
- Temporary files cleaned up on failure

### Error Types
- `TranscriptionServiceError`: Base exception for service errors
- File not found errors
- File format validation errors
- Transcription engine errors
- Database errors

### Recovery
- Jobs can be retried using the job_id
- Failed jobs can be queried and analyzed
- Database transactions ensure consistency

## Performance Considerations

### Lazy Loading
- Transcription engine loaded only when needed
- Model loaded on first transcribe() call
- Reduces initialization time

### Resource Management
- Context manager support for automatic cleanup
- Explicit cleanup methods available
- GPU memory management via engine cleanup

### Batch Optimization
- Single model loading for batch processing
- Efficient error isolation
- Progress tracking per file

## Integration Points

### Database Integration
- Job creation and tracking
- Status updates during processing
- Error logging
- Statistics tracking

### File Management
- Upload with deduplication
- Hash-based duplicate detection
- Storage quota checking
- File metadata tracking

### Transcript Management
- Automatic versioning
- Format conversion
- Export tracking
- Version history

## Testing

Run integration tests:

```bash
# Run all integration tests
python -m pytest tests/integration/test_transcription_service.py -v

# Run specific test
python -m pytest tests/integration/test_transcription_service.py::TestTranscriptionServiceIntegration::test_transcribe_file_complete_workflow -v

# Run with coverage
python -m pytest tests/integration/ --cov=src.core.transcription_service --cov-report=html
```

## Best Practices

1. **Use Context Managers**: Always use `with` statements to ensure proper cleanup
2. **Handle Errors**: Wrap transcription calls in try-except blocks
3. **Monitor Progress**: Use progress callbacks for long-running transcriptions
4. **Check Duplicates**: Let the service handle deduplication automatically
5. **Export Formats**: Export transcripts to multiple formats for flexibility
6. **Batch Processing**: Use batch methods for multiple files
7. **Statistics**: Monitor system health with get_statistics()

## Troubleshooting

### Issue: Transcription fails silently
**Solution**: Check job status in database, review error_message field

### Issue: Duplicate files not detected
**Solution**: Ensure CHECK_DUPLICATES is True in storage_config.py

### Issue: Progress callback not called
**Solution**: Verify callback function signature matches expected format

### Issue: Out of memory errors
**Solution**: Call service.cleanup_resources() between large batches

### Issue: Database locked errors
**Solution**: Ensure only one service instance per process, use connection pooling

## Future Enhancements

- [ ] Async transcription support
- [ ] Distributed job queue integration
- [ ] Real-time streaming transcription
- [ ] Multi-language batch optimization
- [ ] Cloud storage integration
- [ ] WebSocket progress updates
- [ ] REST API wrapper
- [ ] Prometheus metrics export

## See Also

- [TranscriptionEngine Documentation](TRANSCRIPTION_ENGINE.md)
- [Database Schema](DATABASE_SCHEMA.md)
- [File Manager Documentation](FILE_MANAGER.md)
- [Transcript Manager Documentation](TRANSCRIPT_MANAGER.md)
- [Examples Directory](../examples/)
