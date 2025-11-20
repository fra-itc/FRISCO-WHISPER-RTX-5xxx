# API Usage Examples

This document provides practical examples for testing and using the Frisco Whisper RTX API.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [System Endpoints](#system-endpoints)
3. [File Management](#file-management)
4. [Job Management](#job-management)
5. [Transcription Access](#transcription-access)
6. [Search Operations](#search-operations)
7. [Complete Workflows](#complete-workflows)
8. [Error Handling](#error-handling)
9. [WebSocket Examples](#websocket-examples)

---

## Prerequisites

```bash
# Set base URL as environment variable
export API_BASE="http://localhost:8000/api/v1"

# Optional: Set default headers
export HEADERS=(-H "Content-Type: application/json" -H "Accept: application/json")
```

---

## System Endpoints

### Health Check

```bash
# Simple health check
curl $API_BASE/system/health

# Expected response (200 OK):
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-20T10:30:00Z"
}
```

### Get System Status

```bash
# Get comprehensive system status
curl $API_BASE/system/status

# Expected response:
{
  "gpu": {
    "available": true,
    "device_name": "NVIDIA GeForce RTX 5080",
    "vram_gb": 16.0,
    "cuda_version": "12.1",
    "supported_compute_types": ["float16", "float32", "int8"],
    "recommended_compute_type": "float16"
  },
  "jobs": {
    "pending": 3,
    "processing": 1,
    "completed": 127,
    "failed": 2
  },
  "performance": {
    "avg_processing_time": 18.5,
    "total_audio_processed": 3600.0
  },
  "timestamp": "2025-11-20T10:30:00Z"
}
```

### Get GPU Information

```bash
# Get detailed GPU information
curl $API_BASE/system/gpu

# Expected response:
{
  "available": true,
  "device_name": "NVIDIA GeForce RTX 5080",
  "vram_gb": 16.0,
  "cuda_version": "12.1",
  "supported_compute_types": ["float16", "float32", "int8"],
  "recommended_compute_type": "float16"
}
```

### Get Statistics

```bash
# Get usage statistics
curl $API_BASE/system/statistics

# Expected response:
{
  "total_jobs": 133,
  "completed_jobs": 127,
  "failed_jobs": 2,
  "processing_jobs": 1,
  "pending_jobs": 3,
  "total_files": 98,
  "total_size": 1542087680,
  "avg_processing_time": 18.5,
  "total_audio_duration": 3600.0
}
```

### List Available Models

```bash
# Get available Whisper models
curl $API_BASE/models

# Expected response:
{
  "models": [
    {
      "name": "tiny",
      "display_name": "Tiny",
      "size": "tiny",
      "vram_gb": 1.0,
      "speed": "very_fast",
      "accuracy": "basic",
      "languages": 99,
      "description": "Fastest model, suitable for quick tests"
    },
    {
      "name": "large-v3",
      "display_name": "Large V3 (Recommended)",
      "size": "large",
      "vram_gb": 10.0,
      "speed": "slow",
      "accuracy": "excellent",
      "languages": 99,
      "description": "Best quality transcription, recommended for production use"
    }
  ],
  "recommended": "large-v3"
}
```

---

## File Management

### Upload File

```bash
# Upload audio file
curl -X POST $API_BASE/files/upload \
  -F "file=@audio/meeting_recording.m4a" \
  | jq '.'

# Expected response (201 Created):
{
  "file_id": 42,
  "is_new": true,
  "file": {
    "id": 42,
    "file_hash": "a3b5c7d9e1f2...",
    "original_name": "meeting_recording.m4a",
    "file_path": "/uploads/2025/11/meeting_recording.m4a",
    "size_bytes": 15728640,
    "format": "m4a",
    "uploaded_at": "2025-11-20T10:30:00Z"
  },
  "message": "File uploaded successfully"
}

# Upload duplicate file (returns existing file_id)
curl -X POST $API_BASE/files/upload \
  -F "file=@audio/meeting_recording.m4a" \
  | jq '.'

# Expected response (200 OK):
{
  "file_id": 42,
  "is_new": false,
  "file": { ... },
  "message": "File already exists (duplicate detected)"
}

# Save file_id for later use
FILE_ID=$(curl -s -X POST $API_BASE/files/upload \
  -F "file=@audio/test.wav" \
  | jq -r '.file_id')
echo "Uploaded file ID: $FILE_ID"
```

### List Files

```bash
# List all files (default: page 1, limit 50)
curl "$API_BASE/files" | jq '.'

# List with pagination
curl "$API_BASE/files?page=1&limit=20" | jq '.'

# Filter by format
curl "$API_BASE/files?format=m4a&limit=10" | jq '.'

# Expected response:
{
  "files": [
    {
      "id": 42,
      "file_hash": "a3b5c7d9e1f2...",
      "original_name": "meeting_recording.m4a",
      "file_path": "/uploads/2025/11/meeting_recording.m4a",
      "size_bytes": 15728640,
      "format": "m4a",
      "uploaded_at": "2025-11-20T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 98,
    "pages": 2
  }
}
```

### Get File Details

```bash
# Get specific file
curl "$API_BASE/files/42" | jq '.'

# Expected response (200 OK):
{
  "id": 42,
  "file_hash": "a3b5c7d9e1f2...",
  "original_name": "meeting_recording.m4a",
  "file_path": "/uploads/2025/11/meeting_recording.m4a",
  "size_bytes": 15728640,
  "format": "m4a",
  "uploaded_at": "2025-11-20T10:30:00Z"
}

# File not found (404)
curl "$API_BASE/files/99999" | jq '.'

# Expected response:
{
  "error": "NOT_FOUND",
  "message": "File not found",
  "timestamp": "2025-11-20T10:30:00Z"
}
```

### Delete File

```bash
# Delete file (cascade deletes all associated jobs)
curl -X DELETE "$API_BASE/files/42"

# Expected response (204 No Content)
# (empty body)

# Verify deletion
curl "$API_BASE/files/42" | jq '.'
# Returns 404 Not Found
```

---

## Job Management

### Create Job (with File Upload)

```bash
# Upload file and create job in one request
curl -X POST $API_BASE/jobs \
  -F "file=@audio/meeting.m4a" \
  -F "model_size=large-v3" \
  -F "task_type=transcribe" \
  -F "language=it" \
  | jq '.'

# Expected response (201 Created):
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Job created successfully and queued for processing",
  "websocket_url": "ws://localhost:8000/ws/jobs/550e8400-e29b-41d4-a716-446655440000",
  "job": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "file_id": 42,
    "file_name": "meeting.m4a",
    "model_size": "large-v3",
    "status": "pending",
    "task_type": "transcribe",
    "language": "it",
    "created_at": "2025-11-20T10:30:00Z",
    "updated_at": "2025-11-20T10:30:00Z"
  }
}

# Save job_id for later use
JOB_ID=$(curl -s -X POST $API_BASE/jobs \
  -F "file=@audio/test.wav" \
  -F "model_size=tiny" \
  | jq -r '.job_id')
echo "Created job: $JOB_ID"
```

### Create Job (Reference Existing File)

```bash
# Create job using previously uploaded file
curl -X POST $API_BASE/jobs \
  -H "Content-Type: application/json" \
  -d "{
    \"file_id\": 42,
    \"model_size\": \"large-v3\",
    \"task_type\": \"transcribe\",
    \"language\": \"it\",
    \"beam_size\": 5
  }" \
  | jq '.'

# With auto-language detection (omit language field)
curl -X POST $API_BASE/jobs \
  -H "Content-Type: application/json" \
  -d "{
    \"file_id\": 42,
    \"model_size\": \"medium\",
    \"task_type\": \"transcribe\"
  }" \
  | jq '.'

# Translation to English
curl -X POST $API_BASE/jobs \
  -H "Content-Type: application/json" \
  -d "{
    \"file_id\": 42,
    \"model_size\": \"large-v3\",
    \"task_type\": \"translate\"
  }" \
  | jq '.'

# With explicit compute type and device
curl -X POST $API_BASE/jobs \
  -H "Content-Type: application/json" \
  -d "{
    \"file_id\": 42,
    \"model_size\": \"medium\",
    \"compute_type\": \"float16\",
    \"device\": \"cuda\",
    \"beam_size\": 5
  }" \
  | jq '.'
```

### List Jobs

```bash
# List all jobs
curl "$API_BASE/jobs" | jq '.'

# Filter by status
curl "$API_BASE/jobs?status=completed&limit=10" | jq '.'
curl "$API_BASE/jobs?status=failed" | jq '.'
curl "$API_BASE/jobs?status=processing" | jq '.'

# Filter by model
curl "$API_BASE/jobs?model_size=large-v3" | jq '.'

# Sort by created date
curl "$API_BASE/jobs?sort=created_desc&limit=20" | jq '.'
curl "$API_BASE/jobs?sort=updated_desc" | jq '.'

# Pagination
curl "$API_BASE/jobs?page=2&limit=25" | jq '.'

# Combined filters
curl "$API_BASE/jobs?status=completed&model_size=large-v3&page=1&limit=50" | jq '.'

# Expected response:
{
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "file_id": 42,
      "file_name": "meeting.m4a",
      "model_size": "large-v3",
      "status": "completed",
      "task_type": "transcribe",
      "language": "it",
      "detected_language": "it",
      "language_probability": 0.98,
      "compute_type": "float16",
      "device": "cuda",
      "beam_size": 5,
      "created_at": "2025-11-20T10:30:00Z",
      "updated_at": "2025-11-20T10:32:15Z",
      "started_at": "2025-11-20T10:30:05Z",
      "completed_at": "2025-11-20T10:32:15Z",
      "duration_seconds": 125.5,
      "processing_time_seconds": 18.3
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 133,
    "pages": 3
  }
}
```

### Get Job Details

```bash
# Get specific job
curl "$API_BASE/jobs/550e8400-e29b-41d4-a716-446655440000" | jq '.'

# Expected response (200 OK):
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_id": 42,
  "file_name": "meeting.m4a",
  "model_size": "large-v3",
  "status": "completed",
  "task_type": "transcribe",
  "language": "it",
  "detected_language": "it",
  "language_probability": 0.98,
  "created_at": "2025-11-20T10:30:00Z",
  "updated_at": "2025-11-20T10:32:15Z",
  "started_at": "2025-11-20T10:30:05Z",
  "completed_at": "2025-11-20T10:32:15Z",
  "duration_seconds": 125.5,
  "processing_time_seconds": 18.3,
  "file_details": {
    "id": 42,
    "original_name": "meeting.m4a",
    "size_bytes": 15728640,
    "format": "m4a"
  },
  "transcription": {
    "id": 123,
    "text": "Welcome to the meeting...",
    "segment_count": 42
  }
}

# Job not found (404)
curl "$API_BASE/jobs/invalid-uuid" | jq '.'
```

### Poll Job Status

```bash
# Poll until job completes
JOB_ID="550e8400-e29b-41d4-a716-446655440000"

while true; do
  STATUS=$(curl -s "$API_BASE/jobs/$JOB_ID" | jq -r '.status')
  echo "[$(date +%H:%M:%S)] Job status: $STATUS"

  if [ "$STATUS" = "completed" ]; then
    echo "Job completed successfully!"
    break
  elif [ "$STATUS" = "failed" ]; then
    echo "Job failed!"
    curl -s "$API_BASE/jobs/$JOB_ID" | jq '.error_message'
    break
  fi

  sleep 5
done
```

### Cancel Job

```bash
# Cancel pending or processing job
curl -X POST "$API_BASE/jobs/550e8400-e29b-41d4-a716-446655440000/cancel" | jq '.'

# Expected response (200 OK):
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "updated_at": "2025-11-20T10:31:00Z"
}

# Cannot cancel completed job (400)
curl -X POST "$API_BASE/jobs/completed-job-id/cancel" | jq '.'

# Expected response:
{
  "error": "BAD_REQUEST",
  "message": "Cannot cancel completed job",
  "timestamp": "2025-11-20T10:31:00Z"
}
```

### Retry Failed Job

```bash
# Retry a failed job (creates new job)
curl -X POST "$API_BASE/jobs/failed-job-id/retry" | jq '.'

# Expected response (201 Created):
{
  "job_id": "new-job-uuid",
  "status": "pending",
  "message": "Retry job created successfully",
  "websocket_url": "ws://localhost:8000/ws/jobs/new-job-uuid",
  "job": { ... }
}

# Cannot retry non-failed job (400)
curl -X POST "$API_BASE/jobs/completed-job-id/retry" | jq '.'

# Expected response:
{
  "error": "BAD_REQUEST",
  "message": "Can only retry failed jobs",
  "timestamp": "2025-11-20T10:31:00Z"
}
```

### Delete Job

```bash
# Delete job (cascade deletes transcriptions)
curl -X DELETE "$API_BASE/jobs/550e8400-e29b-41d4-a716-446655440000"

# Expected response (204 No Content)
# (empty body)

# Verify deletion
curl "$API_BASE/jobs/550e8400-e29b-41d4-a716-446655440000" | jq '.'
# Returns 404 Not Found
```

---

## Transcription Access

### Get Transcription (JSON)

```bash
# Get transcription in JSON format (default)
curl "$API_BASE/transcriptions/550e8400-e29b-41d4-a716-446655440000" | jq '.'

# Expected response (200 OK):
{
  "id": 123,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "text": "Welcome to the meeting. Today we will discuss the quarterly results...",
  "language": "en",
  "segment_count": 42,
  "segments": [
    {
      "segment_number": 1,
      "start": 0.0,
      "end": 3.5,
      "text": "Welcome to the meeting."
    },
    {
      "segment_number": 2,
      "start": 3.5,
      "end": 8.2,
      "text": "Today we will discuss the quarterly results."
    }
  ],
  "srt_path": "/transcripts/meeting.srt",
  "created_at": "2025-11-20T10:32:15Z"
}

# Job not completed yet (409 Conflict)
curl "$API_BASE/transcriptions/processing-job-id" | jq '.'

# Expected response:
{
  "error": "JOB_NOT_COMPLETED",
  "message": "Job is not yet completed. Current status: processing",
  "timestamp": "2025-11-20T10:31:00Z"
}
```

### Get Transcription (SRT Format)

```bash
# Get as SRT subtitle format
curl "$API_BASE/transcriptions/550e8400-e29b-41d4-a716-446655440000?format=srt"

# Expected response (text/plain):
1
00:00:00,000 --> 00:00:03,500
Welcome to the meeting.

2
00:00:03,500 --> 00:00:08,200
Today we will discuss the quarterly results.

3
00:00:08,200 --> 00:00:12,800
First, let's review the sales figures.
```

### Get Transcription (Plain Text)

```bash
# Get as plain text (no timestamps)
curl "$API_BASE/transcriptions/550e8400-e29b-41d4-a716-446655440000?format=txt"

# Expected response (text/plain):
Welcome to the meeting. Today we will discuss the quarterly results. First, let's review the sales figures.
```

### Download SRT File

```bash
# Download SRT file with proper filename
curl -O -J "$API_BASE/transcriptions/550e8400-e29b-41d4-a716-446655440000/download"

# Or specify output filename
curl "$API_BASE/transcriptions/550e8400-e29b-41d4-a716-446655440000/download" \
  -o meeting_transcript.srt

# Verify download
ls -lh meeting_transcript.srt
cat meeting_transcript.srt
```

---

## Search Operations

### Basic Search

```bash
# Search for keyword
curl "$API_BASE/transcriptions/search?q=artificial+intelligence" | jq '.'

# Expected response (200 OK):
{
  "query": "artificial intelligence",
  "results": [
    {
      "id": 123,
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "text": "...discussing artificial intelligence applications...",
      "language": "en",
      "segment_count": 42,
      "snippet": "...discussing <mark>artificial intelligence</mark> applications...",
      "created_at": "2025-11-20T10:32:15Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 5,
    "pages": 1
  }
}
```

### Search with Filters

```bash
# Search in specific language
curl "$API_BASE/transcriptions/search?q=meeting&language=en&limit=10" | jq '.'

# Search with pagination
curl "$API_BASE/transcriptions/search?q=quarterly+results&page=1&limit=20" | jq '.'

# Multi-word search (URL encoded)
QUERY=$(echo "machine learning algorithms" | sed 's/ /+/g')
curl "$API_BASE/transcriptions/search?q=$QUERY" | jq '.'
```

### Advanced Search Queries

```bash
# Phrase search (exact match)
curl "$API_BASE/transcriptions/search?q=\"quarterly+results\"" | jq '.'

# Boolean operators (FTS5 syntax)
curl "$API_BASE/transcriptions/search?q=machine+AND+learning" | jq '.'
curl "$API_BASE/transcriptions/search?q=AI+OR+\"artificial+intelligence\"" | jq '.'
curl "$API_BASE/transcriptions/search?q=meeting+NOT+cancelled" | jq '.'

# Prefix search
curl "$API_BASE/transcriptions/search?q=techno*" | jq '.'
# Matches: technology, technique, technical, etc.
```

---

## Complete Workflows

### Workflow 1: Upload → Transcribe → Download

```bash
#!/bin/bash
set -e

API_BASE="http://localhost:8000/api/v1"
AUDIO_FILE="audio/meeting.m4a"

echo "=== Starting Transcription Workflow ==="

# Step 1: Upload file
echo "[1/4] Uploading file..."
UPLOAD_RESPONSE=$(curl -s -X POST "$API_BASE/files/upload" \
  -F "file=@$AUDIO_FILE")
FILE_ID=$(echo $UPLOAD_RESPONSE | jq -r '.file_id')
echo "File uploaded: ID=$FILE_ID"

# Step 2: Create job
echo "[2/4] Creating transcription job..."
JOB_RESPONSE=$(curl -s -X POST "$API_BASE/jobs" \
  -H "Content-Type: application/json" \
  -d "{
    \"file_id\": $FILE_ID,
    \"model_size\": \"large-v3\",
    \"task_type\": \"transcribe\",
    \"language\": \"it\"
  }")
JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')
echo "Job created: $JOB_ID"

# Step 3: Poll for completion
echo "[3/4] Waiting for completion..."
while true; do
  JOB_STATUS=$(curl -s "$API_BASE/jobs/$JOB_ID")
  STATUS=$(echo $JOB_STATUS | jq -r '.status')
  echo "  Status: $STATUS"

  if [ "$STATUS" = "completed" ]; then
    SEGMENTS=$(echo $JOB_STATUS | jq -r '.transcription.segment_count')
    LANGUAGE=$(echo $JOB_STATUS | jq -r '.detected_language')
    echo "  Completed: $SEGMENTS segments, language: $LANGUAGE"
    break
  elif [ "$STATUS" = "failed" ]; then
    ERROR=$(echo $JOB_STATUS | jq -r '.error_message')
    echo "  Failed: $ERROR"
    exit 1
  fi

  sleep 5
done

# Step 4: Download results
echo "[4/4] Downloading SRT file..."
OUTPUT_FILE="transcripts/$(basename $AUDIO_FILE .m4a).srt"
curl -s "$API_BASE/transcriptions/$JOB_ID/download" -o "$OUTPUT_FILE"
echo "Saved to: $OUTPUT_FILE"

echo "=== Workflow Complete ==="
```

### Workflow 2: Batch Processing

```bash
#!/bin/bash
set -e

API_BASE="http://localhost:8000/api/v1"
AUDIO_DIR="audio"
TRANSCRIPT_DIR="transcripts"

echo "=== Batch Transcription Workflow ==="

# Find all audio files
FILES=($AUDIO_DIR/*.{m4a,mp3,wav})
TOTAL=${#FILES[@]}
echo "Found $TOTAL files to process"

# Process each file
declare -a JOB_IDS
for i in "${!FILES[@]}"; do
  FILE="${FILES[$i]}"
  NUM=$((i + 1))
  echo "[$NUM/$TOTAL] Processing: $(basename $FILE)"

  # Create job (upload + transcribe)
  JOB_RESPONSE=$(curl -s -X POST "$API_BASE/jobs" \
    -F "file=@$FILE" \
    -F "model_size=large-v3" \
    -F "task_type=transcribe")

  JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')
  JOB_IDS+=($JOB_ID)
  echo "  Job ID: $JOB_ID"
done

# Wait for all jobs to complete
echo ""
echo "Waiting for jobs to complete..."
for i in "${!JOB_IDS[@]}"; do
  JOB_ID="${JOB_IDS[$i]}"
  FILE="${FILES[$i]}"
  NUM=$((i + 1))

  echo "[$NUM/$TOTAL] Waiting for: $(basename $FILE)"

  while true; do
    STATUS=$(curl -s "$API_BASE/jobs/$JOB_ID" | jq -r '.status')

    if [ "$STATUS" = "completed" ]; then
      # Download SRT
      OUTPUT_FILE="$TRANSCRIPT_DIR/$(basename $FILE | sed 's/\.[^.]*$/.srt/')"
      curl -s "$API_BASE/transcriptions/$JOB_ID/download" -o "$OUTPUT_FILE"
      echo "  ✓ Completed: $OUTPUT_FILE"
      break
    elif [ "$STATUS" = "failed" ]; then
      echo "  ✗ Failed"
      break
    fi

    sleep 5
  done
done

echo ""
echo "=== Batch Processing Complete ==="
```

### Workflow 3: Search and Export

```bash
#!/bin/bash

API_BASE="http://localhost:8000/api/v1"
SEARCH_QUERY="$1"

if [ -z "$SEARCH_QUERY" ]; then
  echo "Usage: $0 <search_query>"
  exit 1
fi

echo "Searching for: $SEARCH_QUERY"

# URL encode query
ENCODED_QUERY=$(echo "$SEARCH_QUERY" | sed 's/ /+/g')

# Search
RESULTS=$(curl -s "$API_BASE/transcriptions/search?q=$ENCODED_QUERY&limit=100")
TOTAL=$(echo $RESULTS | jq -r '.pagination.total')

echo "Found $TOTAL results"

# Export to CSV
echo "job_id,language,segment_count,snippet" > search_results.csv

echo $RESULTS | jq -r '.results[] | [.job_id, .language, .segment_count, .snippet] | @csv' \
  >> search_results.csv

echo "Exported to: search_results.csv"

# Download full transcripts
mkdir -p search_exports
echo $RESULTS | jq -r '.results[].job_id' | while read JOB_ID; do
  curl -s "$API_BASE/transcriptions/$JOB_ID/download" \
    -o "search_exports/${JOB_ID}.srt"
  echo "  Downloaded: ${JOB_ID}.srt"
done

echo "Full transcripts saved to: search_exports/"
```

---

## Error Handling

### Handle Common Errors

```bash
# Function to check API response
check_response() {
  local response="$1"
  local http_code=$(echo "$response" | tail -n1)
  local body=$(echo "$response" | head -n-1)

  if [ "$http_code" -ge 400 ]; then
    echo "Error: HTTP $http_code"
    echo "$body" | jq -r '.message'
    return 1
  fi

  echo "$body"
  return 0
}

# Example usage
response=$(curl -s -w "\n%{http_code}" "$API_BASE/jobs/invalid-uuid")
if ! check_response "$response"; then
  echo "Failed to get job"
  exit 1
fi
```

### Retry Logic

```bash
# Retry function with exponential backoff
retry_with_backoff() {
  local max_attempts=5
  local attempt=1
  local delay=2

  while [ $attempt -le $max_attempts ]; do
    echo "Attempt $attempt/$max_attempts..."

    if "$@"; then
      return 0
    fi

    echo "Failed. Retrying in ${delay}s..."
    sleep $delay
    delay=$((delay * 2))
    attempt=$((attempt + 1))
  done

  echo "All retry attempts failed"
  return 1
}

# Example: Create job with retry
retry_with_backoff curl -X POST "$API_BASE/jobs" \
  -F "file=@audio/test.wav" \
  -F "model_size=tiny"
```

---

## WebSocket Examples

### Connect with websocat

```bash
# Install websocat
# On macOS: brew install websocat
# On Linux: cargo install websocat

# Connect to job WebSocket
JOB_ID="550e8400-e29b-41d4-a716-446655440000"
websocat "ws://localhost:8000/ws/jobs/$JOB_ID"

# You'll receive real-time progress updates:
{"type":"progress","job_id":"...","status":"processing","progress":{...}}
{"type":"progress","job_id":"...","status":"processing","progress":{...}}
{"type":"status","job_id":"...","status":"completed","message":"..."}
```

### WebSocket with Python

```python
import asyncio
import websockets
import json

async def monitor_job(job_id):
    uri = f"ws://localhost:8000/ws/jobs/{job_id}"

    async with websockets.connect(uri) as websocket:
        print(f"Connected to job {job_id}")

        while True:
            message = await websocket.recv()
            data = json.loads(message)

            if data['type'] == 'progress':
                progress = data['progress']
                print(f"Progress: {progress['progress_pct']:.1f}% "
                      f"- Segment {progress['segment_number']}")
                print(f"  Text: {progress['text']}")

            elif data['type'] == 'status':
                print(f"Status: {data['status']}")
                if data['status'] == 'completed':
                    print(f"Completed: {data['message']}")
                    break

            elif data['type'] == 'error':
                print(f"Error: {data['message']}")
                break

# Run
asyncio.run(monitor_job("550e8400-e29b-41d4-a716-446655440000"))
```

### WebSocket with JavaScript

```javascript
const jobId = "550e8400-e29b-41d4-a716-446655440000";
const ws = new WebSocket(`ws://localhost:8000/ws/jobs/${jobId}`);

ws.onopen = () => {
  console.log(`Connected to job ${jobId}`);
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case 'progress':
      const progress = data.progress;
      console.log(`Progress: ${progress.progress_pct.toFixed(1)}%`);
      console.log(`Segment ${progress.segment_number}: ${progress.text}`);
      updateProgressBar(progress.progress_pct);
      break;

    case 'status':
      console.log(`Status: ${data.status}`);
      if (data.status === 'completed') {
        console.log('Transcription completed!');
        loadResults(jobId);
        ws.close();
      }
      break;

    case 'error':
      console.error(`Error: ${data.message}`);
      showError(data.message);
      ws.close();
      break;
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket connection closed');
};
```

---

## Summary

This document provides comprehensive examples for:

- Testing all API endpoints with curl
- Complete workflow scripts for common use cases
- Error handling and retry strategies
- Real-time progress monitoring via WebSocket
- Integration examples in multiple languages

For more information, see:
- [API Specification](api.yaml) - Complete OpenAPI 3.0 schema
- [API Design](API_DESIGN.md) - Architecture and design decisions
