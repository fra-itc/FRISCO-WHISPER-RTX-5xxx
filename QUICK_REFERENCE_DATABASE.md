# Database Layer - Quick Reference Card

**FRISCO WHISPER RTX 5xxx - Data Layer API**

---

## Import

```python
from src.data import DatabaseManager, DatabaseError
```

---

## Initialize

```python
db = DatabaseManager('database/transcription.db')

# Or with context manager (auto-close)
with DatabaseManager('database/transcription.db') as db:
    # ... use db ...
```

---

## Job Management

### Create Job

```python
job_id = db.create_job(
    file_path='audio/example.m4a',      # Required
    model_size='medium',                 # Required: tiny, base, small, medium, large-v3
    task_type='transcribe',              # Optional: 'transcribe' or 'translate'
    language='en',                       # Optional: None = auto-detect
    compute_type='float16',              # Optional: float16, float32, int8
    device='cuda',                       # Optional: 'cuda' or 'cpu'
    beam_size=5,                         # Optional: default 5
    duration_seconds=120.5               # Optional: audio duration
)
# Returns: UUID string
```

### Update Job

```python
db.update_job(
    job_id=job_id,
    status='completed',                  # pending, processing, completed, failed
    detected_language='en',
    language_probability=0.98,
    started_at=datetime.now(),
    completed_at=datetime.now(),
    processing_time_seconds=15.3,
    error_message='...'                  # If failed
)
# Returns: bool (True = success)
```

### Get Job

```python
job = db.get_job(job_id)
# Returns: dict or None

# Access fields:
job['status']                # Job status
job['model_size']            # Model used
job['file_name']             # Original filename
job['created_at']            # Creation timestamp
job['transcription_text']    # Full text (if exists)
```

### Query Jobs

```python
# By status
completed = db.get_jobs_by_status('completed', limit=100)

# Recent jobs
recent = db.get_recent_jobs(limit=50)

# Returns: List[dict]
```

### Delete Job

```python
success = db.delete_job(job_id)
# Returns: bool (True = deleted)
# Note: Cascades to transcriptions
```

---

## Transcription Management

### Save Transcription

```python
segments = [
    {'id': 1, 'start': 0.0, 'end': 2.5, 'text': 'Hello world'},
    {'id': 2, 'start': 2.5, 'end': 5.0, 'text': 'This is a test'}
]

transcription_id = db.save_transcription(
    job_id=job_id,
    text='Hello world This is a test',   # Full text
    language='en',                        # Language code
    segments=segments,                    # List of segment dicts
    srt_path='transcripts/example.srt'   # Optional: SRT file path
)
# Returns: int (transcription_id)
```

### Get Transcriptions

```python
transcriptions = db.get_transcriptions(job_id)
# Returns: List[dict]

# Access:
transcriptions[0]['text']           # Full text
transcriptions[0]['language']       # Language
transcriptions[0]['segments']       # Parsed JSON (list)
transcriptions[0]['segment_count']  # Number of segments
```

---

## Search

### Full-Text Search

```python
results = db.search_transcriptions(
    query='artificial intelligence',     # Search query
    language='en',                        # Optional: filter by language
    limit=50                              # Optional: max results
)
# Returns: List[dict]

# Access:
for result in results:
    print(result['text'])       # Full text
    print(result['snippet'])    # Highlighted excerpt
    print(result['job_id'])     # Source job
```

---

## File Management

### Add or Get File (with deduplication)

```python
file_id, is_new = db.add_or_get_file('audio/example.m4a')
# Returns: (int, bool)
#   file_id: Database ID
#   is_new: True if newly added, False if duplicate
```

### Calculate Hash

```python
hash_hex = db.calculate_file_hash('audio/example.m4a')
# Returns: str (64-char hex SHA256)
```

---

## Statistics

```python
stats = db.get_statistics()
# Returns: dict

# Available keys:
stats['total_jobs']              # Total jobs
stats['completed_jobs']          # Completed count
stats['failed_jobs']             # Failed count
stats['processing_jobs']         # Currently processing
stats['pending_jobs']            # Pending count
stats['avg_processing_time']     # Average seconds
stats['total_audio_duration']    # Total seconds
stats['unique_files']            # Unique file count
stats['total_files']             # File count
stats['total_size']              # Total bytes
```

---

## Maintenance

### Cleanup Old Jobs

```python
# Delete completed jobs older than 30 days
deleted = db.cleanup_old_jobs(days=30, status='completed')

# Delete failed jobs older than 7 days
deleted = db.cleanup_old_jobs(days=7, status='failed')

# Returns: int (number deleted)
```

---

## Transactions

### Atomic Operations

```python
try:
    with db.transaction():
        job_id_1 = db.create_job('file1.mp3', 'medium')
        job_id_2 = db.create_job('file2.mp3', 'medium')
        # Both succeed or both fail
except DatabaseError as e:
    print(f"Transaction failed: {e}")
```

---

## Error Handling

```python
from src.data import DatabaseError, DatabaseConnectionError, DatabaseIntegrityError

try:
    db = DatabaseManager('database/transcription.db')
    job_id = db.create_job('audio.mp3', 'medium')

except DatabaseConnectionError as e:
    print(f"Cannot connect: {e}")

except DatabaseIntegrityError as e:
    print(f"Data integrity error: {e}")

except DatabaseError as e:
    print(f"Database error: {e}")
```

---

## Complete Workflow Example

```python
from src.data import DatabaseManager
from datetime import datetime

# Initialize
db = DatabaseManager('database/transcription.db')

# 1. Create job
job_id = db.create_job(
    file_path='audio/interview.m4a',
    model_size='large-v3',
    task_type='transcribe',
    duration_seconds=180.0
)

# 2. Start processing
db.update_job(
    job_id=job_id,
    status='processing',
    started_at=datetime.now()
)

# 3. Process audio (your transcription code here)
# ... transcription happens ...

# 4. Save results
segments = [
    {'id': 1, 'start': 0.0, 'end': 3.2, 'text': 'Welcome to the interview.'},
    {'id': 2, 'start': 3.2, 'end': 7.5, 'text': 'Today we discuss AI.'},
    # ... more segments ...
]

full_text = ' '.join([seg['text'] for seg in segments])

db.save_transcription(
    job_id=job_id,
    text=full_text,
    language='en',
    segments=segments,
    srt_path='transcripts/interview.srt'
)

# 5. Mark complete
db.update_job(
    job_id=job_id,
    status='completed',
    completed_at=datetime.now(),
    detected_language='en',
    language_probability=0.99,
    processing_time_seconds=45.2
)

# 6. Query result
job = db.get_job(job_id)
print(f"Status: {job['status']}")
print(f"Text: {job['transcription_text']}")

# Close
db.close()
```

---

## Common Patterns

### Check if Job Exists

```python
job = db.get_job(job_id)
if job is None:
    print("Job not found")
```

### Handle Failed Jobs

```python
try:
    # ... transcription code ...
except Exception as e:
    db.update_job(
        job_id=job_id,
        status='failed',
        error_message=str(e)
    )
```

### Get All Pending Jobs

```python
pending = db.get_jobs_by_status('pending')
for job in pending:
    print(f"Process: {job['file_name']}")
```

### Search by Keyword

```python
results = db.search_transcriptions('machine learning')
for result in results:
    job = db.get_job(result['job_id'])
    print(f"Found in: {job['file_name']}")
```

---

## Database Tables (Schema)

### files
- `id`, `file_hash`, `original_name`, `file_path`, `size_bytes`, `format`, `uploaded_at`

### transcription_jobs
- `job_id`, `file_id`, `file_name`, `model_size`, `status`, `task_type`, `language`, `detected_language`, `language_probability`, `compute_type`, `device`, `beam_size`, `created_at`, `updated_at`, `started_at`, `completed_at`, `duration_seconds`, `processing_time_seconds`, `error_message`

### transcriptions
- `id`, `job_id`, `text`, `language`, `segment_count`, `segments` (JSON), `srt_path`, `created_at`

### transcriptions_fts (virtual)
- Full-text search index

---

## Views

### v_job_details
Complete job info with file and transcription (JOIN)

### v_job_statistics
Aggregated statistics

---

## Valid Enums

### model_size
`tiny`, `base`, `small`, `medium`, `large`, `large-v2`, `large-v3`

### status
`pending`, `processing`, `completed`, `failed`, `cancelled`

### task_type
`transcribe`, `translate`

### compute_type
`float16`, `float32`, `int8`, `int8_float32`

### device
`cuda`, `cpu`

### format
`m4a`, `mp3`, `wav`, `mp4`, `aac`, `flac`, `opus`, `waptt.opus`

---

## Performance Tips

1. **Use indexes** - All major queries are indexed
2. **Batch operations** - Use transactions for multiple operations
3. **Limit results** - Use `limit` parameter on queries
4. **Close connections** - Use context manager or call `close()`
5. **Full-text search** - Use FTS for text searches (faster than LIKE)

---

## More Information

- **Full Documentation:** `src/data/README.md`
- **Examples:** `python src/data/example_usage.py`
- **Tests:** `python tests/test_database.py`
- **Report:** `DATABASE_SETUP_REPORT.md`

---

**Quick Reference v1.0 - FRISCO WHISPER RTX 5xxx**
