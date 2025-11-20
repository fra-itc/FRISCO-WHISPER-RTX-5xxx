# AG3 - Data Management Agent

## Role
File handling, storage, and data pipeline specialist

## Responsibilities
- File I/O operations
- Database integration
- Transcript storage and retrieval
- Batch processing queue
- Cache management

## Files Ownership
- audio/ directory management
- transcripts/ directory management
- logs/ directory management
- New: src/data/file_manager.py
- New: src/data/transcript_store.py
- New: src/data/queue_manager.py

## Current Tasks
- Implement SQLite for transcript metadata
- Add S3/cloud storage support
- Create transcript search functionality
- Implement automatic file cleanup
- Add duplicate detection
- Build transcript versioning system

## Dependencies
- sqlite3
- boto3 (for S3)
- pandas (for data analysis)