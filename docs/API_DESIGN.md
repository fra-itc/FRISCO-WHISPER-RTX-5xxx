# API Design Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture Principles](#architecture-principles)
3. [API Structure](#api-structure)
4. [Authentication & Security](#authentication--security)
5. [Endpoint Organization](#endpoint-organization)
6. [Error Handling](#error-handling)
7. [Real-Time Communication](#real-time-communication)
8. [Rate Limiting](#rate-limiting)
9. [Pagination](#pagination)
10. [File Upload Strategy](#file-upload-strategy)
11. [Job Lifecycle](#job-lifecycle)
12. [Database Integration](#database-integration)
13. [Performance Considerations](#performance-considerations)
14. [Testing Strategy](#testing-strategy)

---

## Overview

The Frisco Whisper RTX API provides a RESTful interface for audio transcription services powered by OpenAI Whisper with GPU acceleration. The API follows a **job-based asynchronous processing model** where transcription tasks are queued and processed in the background, with real-time progress updates available through WebSocket connections.

### Key Characteristics

- **RESTful Design**: Standard HTTP methods (GET, POST, DELETE) with predictable resource URIs
- **Asynchronous Processing**: Long-running transcriptions use job queues with status polling
- **Real-Time Updates**: WebSocket support for live progress streaming
- **Versioned API**: `/api/v1` prefix for future compatibility
- **Idempotent Operations**: File deduplication via SHA256 hashing
- **Comprehensive Error Handling**: Structured error responses with detailed messages

---

## Architecture Principles

### 1. RESTful Design

The API adheres to REST principles:

- **Resource-Based URLs**: `/files`, `/jobs`, `/transcriptions`
- **HTTP Methods**: GET (read), POST (create), DELETE (delete)
- **Stateless**: Each request contains all necessary information
- **HATEOAS-lite**: Response include relevant links (WebSocket URLs)

### 2. Separation of Concerns

The API acts as a thin layer between the frontend and backend:

```
Frontend (React/Vue)
    ↓
FastAPI REST/WebSocket Layer
    ↓
┌─────────────────┬──────────────────┐
│ TranscriptionEngine │  DatabaseManager │
│ (src/core)          │  (src/data)      │
└─────────────────┴──────────────────┘
```

- **API Layer**: Request validation, routing, response formatting
- **Business Logic**: TranscriptionEngine handles all transcription operations
- **Data Persistence**: DatabaseManager handles all database operations

### 3. Asynchronous Processing

Transcription is compute-intensive and may take minutes for long audio files. The API uses a **job queue pattern**:

1. Client uploads file and creates job → immediate response with job_id
2. Job is queued for background processing
3. Client polls `/jobs/{job_id}` or connects to WebSocket for updates
4. Upon completion, client retrieves results from `/transcriptions/{job_id}`

This prevents HTTP timeouts and provides better user experience.

### 4. API Versioning

All endpoints are prefixed with `/api/v1` to allow future API evolution:

- Breaking changes → new version (`/api/v2`)
- Non-breaking changes → same version
- Multiple versions can coexist during migration

---

## API Structure

### Base URL Structure

```
{protocol}://{host}:{port}/api/{version}/{resource}

Examples:
- http://localhost:8000/api/v1/jobs
- https://api.frisco-whisper.local/api/v1/transcriptions/search
```

### Resource Organization

```
/api/v1/
├── files/                  # File management
│   ├── upload              # Upload new file
│   ├── {file_id}           # Get/delete file
│   └── (list)              # List files
│
├── jobs/                   # Job management
│   ├── (create)            # Create transcription job
│   ├── {job_id}            # Get/delete job
│   ├── {job_id}/cancel     # Cancel job
│   └── {job_id}/retry      # Retry failed job
│
├── transcriptions/         # Results access
│   ├── {job_id}            # Get transcription
│   ├── {job_id}/download   # Download SRT file
│   └── search              # Full-text search
│
├── system/                 # System information
│   ├── health              # Health check
│   ├── status              # System status
│   ├── gpu                 # GPU information
│   └── statistics          # Usage statistics
│
└── models/                 # Model information
    └── (list)              # Available models

WebSocket:
ws://{host}:{port}/ws/jobs/{job_id}
```

---

## Authentication & Security

### Current Implementation: None (v1.0)

For the initial release, authentication is **not implemented** as the application is designed for local/private deployment.

### Future Considerations (v2.0+)

When deploying to shared environments, consider:

#### 1. API Key Authentication

```http
Authorization: Bearer <api_key>
```

Simple header-based authentication suitable for server-to-server communication.

#### 2. JWT Tokens

```http
Authorization: Bearer <jwt_token>
```

For multi-user web applications with user sessions.

#### 3. OAuth 2.0

For third-party integrations and enterprise deployments.

### Security Best Practices

Even without authentication, implement:

1. **Input Validation**: Sanitize all user inputs
2. **File Type Validation**: Only accept allowed audio formats
3. **File Size Limits**: Prevent DoS via large uploads (max 500MB recommended)
4. **Rate Limiting**: Prevent abuse (see Rate Limiting section)
5. **CORS Configuration**: Restrict allowed origins in production
6. **HTTPS**: Use TLS for production deployments

---

## Endpoint Organization

### 1. Files Resource (`/files`)

**Purpose**: Manage audio file uploads and storage

**Design Decisions**:
- Files are deduplicated using SHA256 hashing
- Separate file management from job creation (flexibility)
- Clients can upload once, create multiple jobs with different parameters

**Endpoints**:
- `POST /files/upload` - Upload new file (multipart/form-data)
- `GET /files` - List uploaded files (paginated)
- `GET /files/{file_id}` - Get file details
- `DELETE /files/{file_id}` - Delete file (cascade deletes jobs)

### 2. Jobs Resource (`/jobs`)

**Purpose**: Manage transcription job lifecycle

**Design Decisions**:
- Jobs are identified by UUID for uniqueness and security
- Support both file upload + job creation (convenience) and reference existing file
- Job status follows clear state machine: pending → processing → completed/failed/cancelled

**Endpoints**:
- `POST /jobs` - Create new job (accepts file or file_id)
- `GET /jobs` - List jobs with filtering (status, model, pagination)
- `GET /jobs/{job_id}` - Get job details
- `DELETE /jobs/{job_id}` - Delete job
- `POST /jobs/{job_id}/cancel` - Cancel running job
- `POST /jobs/{job_id}/retry` - Retry failed job

**Job State Machine**:
```
pending → processing → completed
    ↓         ↓            ↑
    └──> cancelled         │
          ↓                │
        failed ──(retry)───┘
```

### 3. Transcriptions Resource (`/transcriptions`)

**Purpose**: Access transcription results

**Design Decisions**:
- Results are immutable once created
- Support multiple output formats (JSON, SRT, TXT)
- Full-text search for finding specific content across all transcriptions

**Endpoints**:
- `GET /transcriptions/{job_id}` - Get transcription (with format query param)
- `GET /transcriptions/{job_id}/download` - Download SRT file
- `GET /transcriptions/search` - Full-text search

### 4. System Resource (`/system`)

**Purpose**: Monitor system health and capabilities

**Design Decisions**:
- Health endpoint for monitoring/orchestration systems
- Detailed status for debugging and performance analysis
- GPU info helps clients choose optimal parameters

**Endpoints**:
- `GET /system/health` - Simple health check
- `GET /system/status` - Detailed system status
- `GET /system/gpu` - GPU capabilities
- `GET /system/statistics` - Usage statistics

### 5. Models Resource (`/models`)

**Purpose**: Discover available AI models

**Design Decisions**:
- Dynamic model list (could be extended in future)
- Includes requirements and recommendations
- Helps clients make informed model selection

**Endpoints**:
- `GET /models` - List available models

---

## Error Handling

### Error Response Format

All errors follow a consistent structure:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error description",
  "details": {
    "field": "Additional context"
  },
  "timestamp": "2025-11-20T10:30:00Z"
}
```

### HTTP Status Codes

| Status | Code | Usage |
|--------|------|-------|
| 200 | OK | Successful GET/POST operation |
| 201 | Created | Resource created successfully |
| 204 | No Content | Successful DELETE operation |
| 400 | Bad Request | Invalid request parameters |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Operation conflict (e.g., job not completed yet) |
| 413 | Payload Too Large | File upload exceeds size limit |
| 415 | Unsupported Media Type | Invalid file format |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Service temporarily unavailable |

### Error Codes

Standardized error codes for client handling:

```python
# Validation Errors
BAD_REQUEST = "Invalid request parameters"
INVALID_MODEL_SIZE = "Model size not supported"
INVALID_LANGUAGE_CODE = "Language code not recognized"
INVALID_FILE_FORMAT = "File format not supported"

# Resource Errors
NOT_FOUND = "Resource not found"
FILE_NOT_FOUND = "Audio file not found"
JOB_NOT_FOUND = "Job not found"

# State Errors
JOB_NOT_COMPLETED = "Job is not yet completed"
JOB_ALREADY_CANCELLED = "Job is already cancelled"
CANNOT_CANCEL_COMPLETED = "Cannot cancel completed job"

# Processing Errors
TRANSCRIPTION_FAILED = "Transcription processing failed"
MODEL_LOAD_FAILED = "Failed to load AI model"
GPU_ERROR = "GPU error occurred"

# System Errors
INTERNAL_SERVER_ERROR = "An unexpected error occurred"
DATABASE_ERROR = "Database operation failed"
STORAGE_ERROR = "File storage error"
```

### Error Handling Strategy

1. **Input Validation**: Validate at API boundary using Pydantic models
2. **Exception Mapping**: Map backend exceptions to appropriate HTTP errors
3. **Logging**: Log all errors with context for debugging
4. **User-Friendly Messages**: Return actionable error messages
5. **Error Recovery**: Provide retry mechanisms for transient failures

---

## Real-Time Communication

### WebSocket Protocol

For real-time progress updates during transcription:

**Connection URL**:
```
ws://localhost:8000/ws/jobs/{job_id}
```

### Message Types

#### 1. Progress Update (Server → Client)

Sent continuously during transcription:

```json
{
  "type": "progress",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": {
    "segment_number": 42,
    "total_segments": null,
    "progress_pct": 35.5,
    "text": "Current segment text being transcribed",
    "start": 120.5,
    "end": 125.3,
    "audio_duration": 350.0
  },
  "timestamp": "2025-11-20T10:31:00Z"
}
```

**Progress Calculation**:
```python
progress_pct = (segment.end / audio_duration) * 100
```

#### 2. Status Update (Server → Client)

Sent when job status changes:

```json
{
  "type": "status",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "Transcription completed successfully",
  "result": {
    "segment_count": 142,
    "language": "en",
    "language_probability": 0.98,
    "processing_time": 18.5
  },
  "timestamp": "2025-11-20T10:32:15Z"
}
```

#### 3. Error (Server → Client)

Sent when job fails:

```json
{
  "type": "error",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "error": "TRANSCRIPTION_FAILED",
  "message": "Model failed to load: CUDA out of memory",
  "timestamp": "2025-11-20T10:31:30Z"
}
```

#### 4. Heartbeat (Bidirectional)

Keep connection alive:

```json
// Client → Server
{"type": "ping"}

// Server → Client
{"type": "pong", "timestamp": "2025-11-20T10:30:00Z"}
```

### Connection Management

1. **Auto-Reconnect**: Client should implement exponential backoff reconnection
2. **Connection Timeout**: Server closes idle connections after 5 minutes
3. **Concurrent Connections**: Multiple clients can connect to same job
4. **Cleanup**: Server cleans up WebSocket resources when job completes

### Implementation with TranscriptionEngine

The WebSocket connects to the `progress_callback` parameter:

```python
def progress_callback(progress_data: dict):
    # Broadcast to all connected WebSocket clients
    await websocket_manager.broadcast(job_id, {
        "type": "progress",
        "job_id": job_id,
        "status": "processing",
        "progress": progress_data,
        "timestamp": datetime.utcnow().isoformat()
    })

# Pass callback to TranscriptionEngine
result = engine.transcribe(
    audio_path=file_path,
    progress_callback=progress_callback
)
```

---

## Rate Limiting

### Strategy

Implement rate limiting to prevent abuse and ensure fair resource allocation:

#### 1. Per-IP Limits (Development)

```python
# Example limits
RATE_LIMITS = {
    "files/upload": "10/hour",      # 10 uploads per hour
    "jobs/create": "20/hour",       # 20 jobs per hour
    "default": "100/minute"         # 100 requests per minute
}
```

#### 2. Per-User Limits (Future with Auth)

```python
USER_LIMITS = {
    "free_tier": "5/day",
    "pro_tier": "100/day",
    "enterprise": "unlimited"
}
```

### Implementation

Use FastAPI middleware with Redis backend:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/files/upload")
@limiter.limit("10/hour")
async def upload_file():
    ...
```

### Rate Limit Headers

Include rate limit info in response headers:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1637596800
```

### 429 Response

When rate limit exceeded:

```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests. Please try again later.",
  "details": {
    "limit": "10/hour",
    "retry_after": 3600
  },
  "timestamp": "2025-11-20T10:30:00Z"
}
```

---

## Pagination

### Query Parameters

Standard pagination parameters:

- `page`: Page number (1-indexed, default: 1)
- `limit`: Items per page (default: 50, max: 100)

### Response Format

All list endpoints include pagination metadata:

```json
{
  "jobs": [...],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 133,
    "pages": 3
  }
}
```

### Implementation

```python
def paginate(query, page: int = 1, limit: int = 50):
    offset = (page - 1) * limit
    total = query.count()
    items = query.limit(limit).offset(offset).all()

    return {
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }
```

### Navigation Links (Optional Enhancement)

Include HATEOAS-style navigation:

```json
{
  "jobs": [...],
  "pagination": {
    "page": 2,
    "limit": 50,
    "total": 133,
    "pages": 3
  },
  "links": {
    "first": "/api/v1/jobs?page=1&limit=50",
    "prev": "/api/v1/jobs?page=1&limit=50",
    "next": "/api/v1/jobs?page=3&limit=50",
    "last": "/api/v1/jobs?page=3&limit=50"
  }
}
```

---

## File Upload Strategy

### Upload Mechanisms

#### 1. Direct Upload (Preferred)

Client uploads file directly to API:

```http
POST /api/v1/files/upload
Content-Type: multipart/form-data

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="audio.m4a"
Content-Type: audio/x-m4a

<binary data>
------WebKitFormBoundary--
```

**Advantages**:
- Simple implementation
- Direct control over file validation

**Disadvantages**:
- API server handles large file transfers
- Not suitable for very large files (>500MB)

#### 2. Presigned URLs (Future Enhancement)

For large files, use cloud storage presigned URLs:

```
1. Client requests upload URL: POST /api/v1/files/upload-url
2. API returns presigned URL
3. Client uploads directly to S3/GCS
4. Client notifies API: POST /api/v1/files/complete
```

### File Validation

Validate files at upload:

```python
ALLOWED_FORMATS = {'m4a', 'mp3', 'wav', 'mp4', 'aac', 'flac', 'opus'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

def validate_file(file: UploadFile):
    # Check extension
    ext = file.filename.split('.')[-1].lower()
    if ext not in ALLOWED_FORMATS:
        raise HTTPException(415, "Unsupported file format")

    # Check size (if available)
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large")

    # Check MIME type
    if not file.content_type.startswith('audio/'):
        raise HTTPException(415, "Not an audio file")
```

### File Storage

```
storage/
├── uploads/
│   └── {year}/
│       └── {month}/
│           └── {file_hash[:2]}/
│               └── {file_hash}.{ext}
└── transcripts/
    └── {year}/
        └── {month}/
            └── {job_id}.srt
```

**Storage Strategy**:
- Files organized by date and hash prefix (distributed I/O)
- Original filename stored in database
- Automatic cleanup of orphaned files

### Deduplication

Files are deduplicated using SHA256 hashing:

```python
file_hash = hashlib.sha256(file_content).hexdigest()

# Check if hash exists
existing = db.get_file_by_hash(file_hash)
if existing:
    return {"file_id": existing.id, "is_new": False}

# Store new file
file_id = db.add_file(file_hash, filename, path)
return {"file_id": file_id, "is_new": True}
```

---

## Job Lifecycle

### State Machine

```
┌─────────┐
│ PENDING │ Initial state when job is created
└────┬────┘
     │
     ↓
┌────────────┐
│ PROCESSING │ Worker picked up job and started transcription
└──┬─────┬───┘
   │     │
   │     ↓
   │  ┌────────┐
   │  │ FAILED │ Error during processing (can retry)
   │  └────────┘
   │
   ↓
┌───────────┐
│ COMPLETED │ Transcription successful, results available
└───────────┘

   ↓ (user action)
┌───────────┐
│ CANCELLED │ User cancelled before/during processing
└───────────┘
```

### State Transitions

| From | To | Trigger | Reversible |
|------|---|---------|-----------|
| pending | processing | Worker starts job | No |
| processing | completed | Transcription succeeds | No |
| processing | failed | Error occurs | Yes (retry) |
| pending | cancelled | User cancels | No |
| processing | cancelled | User cancels | No |
| failed | pending | User retries | No (creates new job) |

### Job Processing Flow

```python
# 1. Job Creation
job_id = db.create_job(
    file_path=file_path,
    model_size=model_size,
    task_type=task_type,
    language=language
)

# 2. Queue Job
await job_queue.enqueue(job_id)

# 3. Worker Processes Job
async def process_job(job_id):
    # Update status
    db.update_job(job_id, status='processing', started_at=datetime.now())

    # Create engine
    engine = TranscriptionEngine(model_size=job.model_size)

    # Transcribe with progress callback
    result = engine.transcribe(
        audio_path=job.file_path,
        language=job.language,
        progress_callback=lambda p: broadcast_progress(job_id, p)
    )

    if result.success:
        # Save results
        db.save_transcription(
            job_id=job_id,
            text=result.text,
            segments=result.segments,
            srt_path=result.output_path
        )

        # Update job
        db.update_job(
            job_id=job_id,
            status='completed',
            completed_at=datetime.now(),
            processing_time=result.duration,
            detected_language=result.language,
            language_probability=result.language_probability
        )
    else:
        # Handle failure
        db.update_job(
            job_id=job_id,
            status='failed',
            completed_at=datetime.now(),
            error_message=result.error
        )
```

### Job Queue

Use background task queue for job processing:

**Option 1: Celery (Production)**
```python
from celery import Celery

celery = Celery('whisper', broker='redis://localhost:6379')

@celery.task
def process_transcription(job_id):
    ...
```

**Option 2: FastAPI BackgroundTasks (Simple)**
```python
from fastapi import BackgroundTasks

@app.post("/api/v1/jobs")
async def create_job(background_tasks: BackgroundTasks):
    job_id = create_job_in_db()
    background_tasks.add_task(process_job, job_id)
    return {"job_id": job_id}
```

---

## Database Integration

### DatabaseManager Integration

The API leverages the existing `DatabaseManager` class:

```python
from src.data.database import DatabaseManager

# Initialize once at startup
db = DatabaseManager('database/transcription.db')

# Use in endpoints
@app.post("/api/v1/jobs")
async def create_job(request: CreateJobRequest):
    job_id = db.create_job(
        file_path=request.file_path,
        model_size=request.model_size,
        task_type=request.task_type,
        language=request.language
    )
    return {"job_id": job_id}
```

### Thread Safety

DatabaseManager uses thread-local connections, safe for FastAPI's async workers:

```python
# Each request gets its own connection
@app.get("/api/v1/jobs/{job_id}")
async def get_job(job_id: str):
    # Safe: thread-local connection
    job = db.get_job(job_id)
    return job
```

### Transactions

Use transactions for multi-step operations:

```python
@app.post("/api/v1/jobs/{job_id}/retry")
async def retry_job(job_id: str):
    with db.transaction():
        # Get original job
        original = db.get_job(job_id)
        if original['status'] != 'failed':
            raise HTTPException(400, "Can only retry failed jobs")

        # Create new job
        new_job_id = db.create_job(
            file_path=original['file_path'],
            model_size=original['model_size'],
            # ... other params
        )

    return {"job_id": new_job_id}
```

### Connection Pooling

For high-concurrency deployments, consider connection pooling:

```python
# Use async SQLAlchemy for better performance
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    "sqlite+aiosqlite:///database/transcription.db",
    pool_size=20,
    max_overflow=10
)
```

---

## Performance Considerations

### 1. Database Optimization

Already implemented in `DatabaseManager`:
- WAL mode for concurrent reads/writes
- Proper indexes on frequent query columns
- FTS5 for full-text search

### 2. Caching

Implement caching for frequently accessed data:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_gpu_info():
    return TranscriptionEngine().get_gpu_info()

@app.get("/api/v1/system/gpu")
async def gpu_info():
    return get_gpu_info()
```

### 3. Async I/O

Use async for I/O-bound operations:

```python
import aiofiles

async def save_upload(file: UploadFile, path: str):
    async with aiofiles.open(path, 'wb') as f:
        while chunk := await file.read(8192):
            await f.write(chunk)
```

### 4. Streaming Responses

Stream large files:

```python
from fastapi.responses import StreamingResponse

@app.get("/api/v1/transcriptions/{job_id}/download")
async def download(job_id: str):
    async def file_stream():
        async with aiofiles.open(srt_path, 'rb') as f:
            while chunk := await f.read(8192):
                yield chunk

    return StreamingResponse(
        file_stream(),
        media_type="application/x-subrip"
    )
```

### 5. Connection Management

Reuse TranscriptionEngine instances:

```python
# Global engine pool
engine_pool = {}

def get_engine(model_size: str):
    if model_size not in engine_pool:
        engine_pool[model_size] = TranscriptionEngine(model_size)
    return engine_pool[model_size]
```

### 6. Monitoring

Add performance monitoring:

```python
import time
from fastapi import Request

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

---

## Testing Strategy

### 1. Unit Tests

Test individual endpoints:

```python
from fastapi.testclient import TestClient

def test_create_job(client: TestClient, sample_file):
    response = client.post(
        "/api/v1/jobs",
        files={"file": sample_file},
        data={"model_size": "tiny"}
    )
    assert response.status_code == 201
    assert "job_id" in response.json()
```

### 2. Integration Tests

Test full workflow:

```python
def test_transcription_workflow(client: TestClient):
    # Upload file
    file_response = client.post("/api/v1/files/upload", ...)
    file_id = file_response.json()["file_id"]

    # Create job
    job_response = client.post("/api/v1/jobs", json={
        "file_id": file_id,
        "model_size": "tiny"
    })
    job_id = job_response.json()["job_id"]

    # Wait for completion (in test, run synchronously)
    process_job_sync(job_id)

    # Get transcription
    transcript = client.get(f"/api/v1/transcriptions/{job_id}")
    assert transcript.status_code == 200
```

### 3. WebSocket Tests

Test real-time updates:

```python
from fastapi.testclient import TestClient

def test_websocket_progress(client: TestClient):
    with client.websocket_connect(f"/ws/jobs/{job_id}") as websocket:
        # Trigger job processing
        process_job_in_background(job_id)

        # Receive progress updates
        while True:
            data = websocket.receive_json()
            assert data["type"] in ["progress", "status", "error"]
            if data["type"] == "status" and data["status"] == "completed":
                break
```

### 4. Load Tests

Test performance under load:

```python
# Using locust
from locust import HttpUser, task

class TranscriptionUser(HttpUser):
    @task
    def create_job(self):
        with open("test_audio.wav", "rb") as f:
            self.client.post("/api/v1/jobs", files={"file": f})
```

---

## Example Usage

### Complete Workflow with curl

```bash
# 1. Check system status
curl http://localhost:8000/api/v1/system/status

# 2. Upload audio file
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@meeting_recording.m4a" \
  > upload_response.json

FILE_ID=$(jq -r '.file_id' upload_response.json)

# 3. Create transcription job
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d "{
    \"file_id\": $FILE_ID,
    \"model_size\": \"large-v3\",
    \"task_type\": \"transcribe\",
    \"language\": \"it\"
  }" \
  > job_response.json

JOB_ID=$(jq -r '.job_id' job_response.json)

# 4. Poll job status
while true; do
  STATUS=$(curl -s http://localhost:8000/api/v1/jobs/$JOB_ID | jq -r '.status')
  echo "Job status: $STATUS"
  if [ "$STATUS" = "completed" ]; then
    break
  fi
  sleep 5
done

# 5. Get transcription results
curl http://localhost:8000/api/v1/transcriptions/$JOB_ID \
  > transcription.json

# 6. Download SRT file
curl http://localhost:8000/api/v1/transcriptions/$JOB_ID/download \
  -o transcription.srt

# 7. Search transcriptions
curl "http://localhost:8000/api/v1/transcriptions/search?q=artificial+intelligence&limit=10"
```

### JavaScript/TypeScript Example

```typescript
// 1. Upload file and create job
async function transcribeAudio(file: File, modelSize: string) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('model_size', modelSize);
  formData.append('language', 'it');

  const response = await fetch('http://localhost:8000/api/v1/jobs', {
    method: 'POST',
    body: formData
  });

  const { job_id, websocket_url } = await response.json();

  // 2. Connect to WebSocket for real-time updates
  const ws = new WebSocket(websocket_url);

  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    switch (message.type) {
      case 'progress':
        updateProgressBar(message.progress.progress_pct);
        displaySegment(message.progress.text);
        break;

      case 'status':
        if (message.status === 'completed') {
          loadTranscription(job_id);
          ws.close();
        }
        break;

      case 'error':
        showError(message.message);
        ws.close();
        break;
    }
  };

  return job_id;
}

// 3. Load completed transcription
async function loadTranscription(jobId: string) {
  const response = await fetch(
    `http://localhost:8000/api/v1/transcriptions/${jobId}?format=json`
  );
  const transcription = await response.json();

  displayTranscription(transcription);
}

// 4. Download SRT file
function downloadSRT(jobId: string) {
  window.location.href =
    `http://localhost:8000/api/v1/transcriptions/${jobId}/download`;
}

// 5. Search transcriptions
async function searchTranscriptions(query: string) {
  const response = await fetch(
    `http://localhost:8000/api/v1/transcriptions/search?` +
    `q=${encodeURIComponent(query)}&limit=20`
  );
  const results = await response.json();

  displaySearchResults(results.results);
}
```

---

## Summary

This API design provides:

- **Clean REST architecture** with clear resource boundaries
- **Asynchronous processing** for long-running transcriptions
- **Real-time updates** via WebSocket for better UX
- **Comprehensive error handling** with actionable messages
- **Scalability considerations** for future growth
- **Security best practices** even without authentication
- **Performance optimizations** for production deployment
- **Testability** at all levels

The design is **production-ready** while remaining **simple to implement** by leveraging the existing `TranscriptionEngine` and `DatabaseManager` components.
