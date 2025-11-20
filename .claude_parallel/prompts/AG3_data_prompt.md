# AG3 Data Management Agent - Operational Prompt

You are AG3, the Data Management specialist for the FRISCO-WHISPER-RTX project.

## IMMEDIATE TASK
Implement a robust data layer with SQLite database and cloud storage integration.

## STEP-BY-STEP EXECUTION

### Step 1: Setup Database Structure (10 min)
```bash
mkdir -p C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx\src\data
mkdir -p C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx\database
```

### Step 2: Create Database Schema (15 min)
Create `src/data/database.py`:
```python
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
import json

class TranscriptDatabase:
    def __init__(self, db_path: str = "database/transcripts.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            file_size INTEGER,
            duration_seconds REAL,
            language TEXT,
            model_used TEXT,
            compute_type TEXT,
            transcription_text TEXT,
            srt_content TEXT,
            word_count INTEGER,
            confidence_score REAL,
            processing_time REAL,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transcription_id INTEGER,
            segment_index INTEGER,
            start_time REAL,
            end_time REAL,
            text TEXT,
            confidence REAL,
            FOREIGN KEY (transcription_id) REFERENCES transcriptions(id)
        )
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_file_hash ON transcriptions(file_hash)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_status ON transcriptions(status)
        """)

        conn.commit()
        conn.close()

    def insert_transcription(self, job_data: Dict) -> int:
        """Insert new transcription job"""
        # Implementation
        pass

    def update_status(self, job_id: str, status: str, error: Optional[str] = None):
        """Update job status"""
        # Implementation
        pass

    def get_transcription(self, job_id: str) -> Optional[Dict]:
        """Get transcription by job ID"""
        # Implementation
        pass

    def search_transcripts(self, query: str) -> List[Dict]:
        """Full-text search in transcripts"""
        # Implementation
        pass
```

### Step 3: Implement File Manager (20 min)
Create `src/data/file_manager.py`:
```python
import hashlib
import shutil
from pathlib import Path
from typing import Optional, Tuple
import os

class FileManager:
    def __init__(self, base_dir: str = "C:\\PROJECTS\\FRISCO-WHISPER-RTX-5xxx"):
        self.base_dir = Path(base_dir)
        self.audio_dir = self.base_dir / "audio"
        self.transcripts_dir = self.base_dir / "transcripts"
        self.temp_dir = self.base_dir / "temp"
        self.archive_dir = self.base_dir / "archive"

        # Create directories
        for dir_path in [self.audio_dir, self.transcripts_dir,
                         self.temp_dir, self.archive_dir]:
            dir_path.mkdir(exist_ok=True)

    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def check_duplicate(self, file_path: Path) -> Optional[str]:
        """Check if file already exists by hash"""
        file_hash = self.calculate_file_hash(file_path)
        # Check in database for existing hash
        return file_hash

    def organize_files(self, file_path: Path) -> Path:
        """Organize files by date/type"""
        date_dir = self.audio_dir / datetime.now().strftime("%Y-%m-%d")
        date_dir.mkdir(exist_ok=True)
        return date_dir / file_path.name

    def cleanup_old_files(self, days: int = 30):
        """Remove files older than specified days"""
        cutoff_time = datetime.now() - timedelta(days=days)
        for file_path in self.temp_dir.iterdir():
            if file_path.stat().st_mtime < cutoff_time.timestamp():
                file_path.unlink()

    def archive_completed(self, job_id: str):
        """Archive completed transcription"""
        # Move to archive directory
        pass
```

### Step 4: Add Cloud Storage Support (15 min)
Create `src/data/cloud_storage.py`:
```python
import boto3
from typing import Optional
import os

class CloudStorage:
    def __init__(self, provider: str = "s3"):
        self.provider = provider
        if provider == "s3":
            self.client = boto3.client('s3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
                aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
            )
            self.bucket = os.getenv('S3_BUCKET', 'frisco-whisper')

    def upload_transcript(self, local_path: str, job_id: str) -> str:
        """Upload transcript to cloud"""
        key = f"transcripts/{job_id}/{os.path.basename(local_path)}"
        self.client.upload_file(local_path, self.bucket, key)
        return f"s3://{self.bucket}/{key}"

    def download_transcript(self, job_id: str, local_path: str):
        """Download transcript from cloud"""
        key = f"transcripts/{job_id}/transcript.srt"
        self.client.download_file(self.bucket, key, local_path)

    def list_transcripts(self, prefix: str = "") -> list:
        """List all transcripts in cloud"""
        response = self.client.list_objects_v2(
            Bucket=self.bucket,
            Prefix=f"transcripts/{prefix}"
        )
        return response.get('Contents', [])
```

### Step 5: Create Queue Manager (10 min)
Create `src/data/queue_manager.py`:
```python
from queue import PriorityQueue
from dataclasses import dataclass
from typing import Optional
import threading

@dataclass
class TranscriptionJob:
    priority: int
    job_id: str
    file_path: str
    settings: dict

    def __lt__(self, other):
        return self.priority < other.priority

class QueueManager:
    def __init__(self, max_concurrent: int = 2):
        self.queue = PriorityQueue()
        self.active_jobs = {}
        self.max_concurrent = max_concurrent
        self.lock = threading.Lock()

    def add_job(self, job: TranscriptionJob):
        """Add job to queue"""
        self.queue.put(job)

    def get_next_job(self) -> Optional[TranscriptionJob]:
        """Get next job from queue"""
        with self.lock:
            if len(self.active_jobs) < self.max_concurrent:
                if not self.queue.empty():
                    job = self.queue.get()
                    self.active_jobs[job.job_id] = job
                    return job
        return None

    def complete_job(self, job_id: str):
        """Mark job as completed"""
        with self.lock:
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]

    def get_queue_status(self) -> dict:
        """Get current queue status"""
        return {
            "queued": self.queue.qsize(),
            "active": len(self.active_jobs),
            "max_concurrent": self.max_concurrent
        }
```

## DATABASE QUERIES

```sql
-- Find duplicates
SELECT file_hash, COUNT(*) as count
FROM transcriptions
GROUP BY file_hash
HAVING count > 1;

-- Get recent transcriptions
SELECT * FROM transcriptions
WHERE created_at > datetime('now', '-7 days')
ORDER BY created_at DESC;

-- Search in transcripts
SELECT * FROM transcriptions
WHERE transcription_text LIKE '%search_term%'
ORDER BY created_at DESC;

-- Get statistics
SELECT
    COUNT(*) as total_files,
    SUM(duration_seconds) as total_duration,
    AVG(processing_time) as avg_processing_time,
    COUNT(DISTINCT language) as unique_languages
FROM transcriptions;
```

## OUTPUT FILES
1. `src/data/database.py` - SQLite database manager
2. `src/data/file_manager.py` - File organization
3. `src/data/cloud_storage.py` - S3/cloud integration
4. `src/data/queue_manager.py` - Job queue system
5. `database/schema.sql` - Database schema

## SUCCESS CRITERIA
- Database operations < 10ms
- Duplicate detection working
- Cloud backup automatic
- Search functionality fast
- Queue system stable

EXECUTE NOW. Ensure data integrity and scalability.