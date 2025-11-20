# Transcript Versioning System Documentation

## Overview

The FRISCO WHISPER RTX 5xxx transcript versioning system provides comprehensive version control for transcription results, allowing users to:

- Save and retrieve transcripts with automatic versioning
- Track complete history of all changes
- Compare different versions
- Export to multiple formats (SRT, VTT, JSON, TXT, CSV)
- Rollback to previous versions
- Manage version retention policies

## Architecture

### Components

1. **DatabaseManager** - Core database operations and connection management
2. **TranscriptManager** - High-level transcript and versioning operations
3. **FormatConverter** - Multi-format export capabilities
4. **DiffGenerator** - Version comparison and diff generation

### Database Schema

#### transcriptions table
- Stores the main transcript record
- Links to transcription jobs
- Maintains current state

#### transcript_versions table
- Stores all versions of each transcript
- Automatic versioning via database triggers
- Tracks change metadata (who, when, why)

#### export_history table
- Audit trail of all exports
- Tracks format and version exported

## Core Features

### 1. Automatic Versioning

Every transcript operation creates versions automatically:

```python
from src.data import DatabaseManager, TranscriptManager

db = DatabaseManager('database/transcription.db')
tm = TranscriptManager(db)

# Initial save creates version 1
transcript_id = tm.save_transcript(
    job_id=job_id,
    text="Full transcript text",
    segments=[
        {"start": 0.0, "end": 5.0, "text": "First segment"},
        {"start": 5.0, "end": 10.0, "text": "Second segment"}
    ],
    language='en'
)

# Update creates version 2 automatically
tm.update_transcript(
    transcript_id=transcript_id,
    text="Updated transcript text",
    segments=[...],
    created_by='user@example.com',
    change_note='Improved accuracy'
)
```

### 2. Version Retrieval

Get any version of a transcript:

```python
# Get current version
current = tm.get_transcript(transcript_id)

# Get specific version
v1 = tm.get_transcript(transcript_id, version=1)
v2 = tm.get_transcript(transcript_id, version=2)

# Get all versions
versions = tm.get_versions(transcript_id)
for v in versions:
    print(f"v{v['version_number']}: {v['change_note']}")
```

### 3. Version Comparison

Compare any two versions:

```python
comparison = tm.compare_versions(
    transcript_id=transcript_id,
    version1=1,
    version2=2
)

# Text differences
text_diff = comparison['text_diff']
print(f"Character change: {text_diff['char_diff']}")
print(f"Word change: {text_diff['word_diff']}")

# Segment differences
seg_diff = comparison['segment_diff']
print(f"Segment change: {seg_diff['segment_diff']}")
print(f"Similarity: {seg_diff['similarity_percent']}%")
```

### 4. Multi-Format Export

Export to any supported format:

#### SRT (SubRip Subtitle Format)
```python
tm.export_transcript(
    transcript_id=transcript_id,
    format_name='srt',
    output_path='output.srt'
)
```

Output:
```
1
00:00:00,000 --> 00:00:05,000
First segment text

2
00:00:05,000 --> 00:00:10,000
Second segment text
```

#### VTT (WebVTT)
```python
tm.export_transcript(
    transcript_id=transcript_id,
    format_name='vtt',
    output_path='output.vtt'
)
```

Output:
```
WEBVTT

00:00:00.000 --> 00:00:05.000
First segment text

00:00:05.000 --> 00:00:10.000
Second segment text
```

#### JSON (Structured Data)
```python
tm.export_transcript(
    transcript_id=transcript_id,
    format_name='json',
    output_path='output.json'
)
```

Output:
```json
{
  "format": "whisper-json",
  "version": "1.0",
  "metadata": {
    "language": "en",
    "job_id": "uuid-here"
  },
  "text": "Full transcript text...",
  "segment_count": 2,
  "segments": [
    {"start": 0.0, "end": 5.0, "text": "First segment"},
    {"start": 5.0, "end": 10.0, "text": "Second segment"}
  ]
}
```

#### TXT (Plain Text)
```python
# Without timestamps
tm.export_transcript(
    transcript_id=transcript_id,
    format_name='txt',
    output_path='output.txt',
    include_timestamps=False
)

# With timestamps
tm.export_transcript(
    transcript_id=transcript_id,
    format_name='txt',
    output_path='output.txt',
    include_timestamps=True
)
```

#### CSV (Tabular Format)
```python
tm.export_transcript(
    transcript_id=transcript_id,
    format_name='csv',
    output_path='output.csv'
)
```

Output:
```csv
index,start,end,duration,text
1,0.000,5.000,5.000,"First segment"
2,5.000,10.000,5.000,"Second segment"
```

### 5. Version Rollback

Restore previous versions non-destructively:

```python
# Rollback to version 2 (creates new version with old content)
new_version = tm.rollback_to_version(
    transcript_id=transcript_id,
    version_number=2,
    created_by='user@example.com',
    change_note='Reverted to better version'
)

# History is preserved - nothing is deleted
# If you had versions 1, 2, 3, 4
# After rollback to v2, you'll have: 1, 2, 3, 4, 5 (where 5 = copy of 2)
```

### 6. Version History

Get complete audit trail:

```python
history = tm.get_version_history(transcript_id)

print(f"Total versions: {history['version_count']}")
print(f"Current version: {history['current_version']}")

for v in history['versions']:
    print(f"v{v['version_number']}: {v['change_note']}")
    print(f"  By: {v['created_by']}")
    print(f"  At: {v['created_at']}")

# Export history included
for exp in history['exports']:
    print(f"Exported as {exp['format_name']} at {exp['exported_at']}")
```

### 7. Version Retention

Manage storage with retention policies:

```python
# Keep only the 10 most recent versions
deleted_count = tm.delete_old_versions(
    transcript_id=transcript_id,
    keep_count=10
)

print(f"Deleted {deleted_count} old versions")
```

## Format Converter API

The `FormatConverter` class can be used standalone:

```python
from src.data import FormatConverter

converter = FormatConverter()

segments = [
    {"start": 0.0, "end": 5.0, "text": "Sample text"}
]

# Convert to any format
srt = converter.to_srt(segments)
vtt = converter.to_vtt(segments)
json_str = converter.to_json(segments)
txt = converter.to_txt(segments)
csv = converter.to_csv(segments)

# Or use the dispatcher
content = converter.convert(segments, format_name='srt')

# Validate segments before conversion
if converter.validate_segments(segments):
    content = converter.convert(segments, 'vtt')

# Get format information
info = converter.get_format_info('srt')
print(f"MIME type: {info['mime_type']}")
print(f"Extension: {info['extension']}")
```

## Database Triggers

The system uses SQLite triggers for automatic versioning:

### create_initial_version
- Fires on INSERT into transcriptions
- Creates version 1 automatically
- Marks it as current version

### create_version_on_update
- Fires on UPDATE of transcriptions.text or transcriptions.segments
- Unmarks previous current version
- Creates new version with incremented number
- Marks new version as current

## Best Practices

### 1. Always Use Change Notes
```python
tm.update_transcript(
    transcript_id=transcript_id,
    text=new_text,
    segments=new_segments,
    created_by='user@example.com',
    change_note='Fixed speaker identification in segment 3'
)
```

### 2. Set User Attribution
```python
# Use actual user identifiers
tm.save_transcript(
    job_id=job_id,
    text=text,
    segments=segments,
    created_by='user@example.com'  # Not 'system'
)
```

### 3. Implement Retention Policies
```python
# Cleanup old versions regularly
import schedule

def cleanup_old_versions():
    for transcript_id in get_all_transcript_ids():
        tm.delete_old_versions(transcript_id, keep_count=10)

# Run weekly
schedule.every().week.do(cleanup_old_versions)
```

### 4. Export Before Major Changes
```python
# Backup current version before major update
tm.export_transcript(
    transcript_id=transcript_id,
    format_name='json',
    output_path=f'backups/transcript_{transcript_id}_backup.json'
)

# Then make changes
tm.update_transcript(...)
```

### 5. Use Version Comparison
```python
# Check impact before rollback
comparison = tm.compare_versions(transcript_id, current_version, target_version)

if comparison['segment_diff']['similarity_percent'] < 50:
    print("Warning: Large difference detected!")
    # Ask for confirmation
```

## Error Handling

```python
from src.data import (
    TranscriptError,
    TranscriptNotFoundError,
    VersionNotFoundError
)

try:
    transcript = tm.get_transcript(transcript_id)
except TranscriptNotFoundError:
    print("Transcript does not exist")
except VersionNotFoundError:
    print("Requested version does not exist")
except TranscriptError as e:
    print(f"General transcript error: {e}")
```

## Performance Considerations

### Indexing
The system includes optimized indexes for:
- Transcript ID lookups
- Version number queries
- Current version retrieval
- Temporal queries (created_at)

### Storage Optimization
- Segments stored as compressed JSON
- Old versions can be archived/deleted
- Export history tracks files without duplicating data

### Query Optimization
```python
# Efficient: Get only version metadata
versions = tm.get_versions(transcript_id)

# Less efficient: Get full version content
for v in versions:
    full = tm.get_transcript(transcript_id, version=v['version_number'])
```

## Migration Guide

### Applying the Versioning Migration

The versioning system requires migration 002:

```python
from src.data import DatabaseManager

# DatabaseManager automatically applies migrations
db = DatabaseManager('database/transcription.db')
# Migration 002 applied automatically if needed
```

### Manual Migration Application

If needed, you can apply manually:

```sql
-- Run: database/migrations/002_add_versioning.sql
sqlite3 database/transcription.db < database/migrations/002_add_versioning.sql
```

## Testing

Run the comprehensive test suite:

```bash
# Run all transcript manager tests
pytest tests/unit/test_transcript_manager.py -v

# Run specific test class
pytest tests/unit/test_transcript_manager.py::TestFormatConverter -v

# Run integration tests
pytest tests/unit/test_transcript_manager.py::TestTranscriptWorkflow -v
```

## Example Use Cases

### Use Case 1: Iterative Improvement
```python
# Initial automated transcription
transcript_id = tm.save_transcript(job_id, auto_text, auto_segments)

# First manual review
tm.update_transcript(
    transcript_id, reviewed_text, reviewed_segments,
    created_by='reviewer1',
    change_note='First review pass - fixed obvious errors'
)

# Second review by different person
tm.update_transcript(
    transcript_id, final_text, final_segments,
    created_by='reviewer2',
    change_note='Second review - verified technical terms'
)

# Can always see evolution
history = tm.get_version_history(transcript_id)
```

### Use Case 2: A/B Testing
```python
# Create variation A
tm.update_transcript(
    transcript_id, variant_a_text, variant_a_segments,
    change_note='Variant A: Conservative segmentation'
)

# Create variation B
tm.update_transcript(
    transcript_id, variant_b_text, variant_b_segments,
    change_note='Variant B: Aggressive segmentation'
)

# Compare
comparison = tm.compare_versions(transcript_id, version_a, version_b)

# Export both for user testing
tm.export_transcript(transcript_id, 'srt', 'variant_a.srt', version=version_a)
tm.export_transcript(transcript_id, 'srt', 'variant_b.srt', version=version_b)
```

### Use Case 3: Compliance and Audit
```python
# Track all changes for compliance
history = tm.get_version_history(transcript_id)

for v in history['versions']:
    log_audit_entry(
        transcript_id=transcript_id,
        version=v['version_number'],
        changed_by=v['created_by'],
        changed_at=v['created_at'],
        reason=v['change_note']
    )
```

## Statistics and Monitoring

```python
# Get system-wide statistics
stats = tm.get_statistics()

print(f"Total transcripts: {stats['total_transcripts']}")
print(f"Total versions: {stats['total_versions']}")
print(f"Average versions per transcript: {stats['avg_versions_per_transcript']:.2f}")
print(f"Most popular export format: {max(stats['exports_by_format'].items(), key=lambda x: x[1])}")
```

## API Reference

### TranscriptManager

#### Methods

- `save_transcript(job_id, text, segments, language, srt_path, created_by)` - Save new transcript
- `update_transcript(transcript_id, text, segments, created_by, change_note)` - Update with versioning
- `get_transcript(transcript_id, version)` - Get specific version
- `get_versions(transcript_id)` - List all versions
- `compare_versions(transcript_id, version1, version2)` - Compare versions
- `rollback_to_version(transcript_id, version_number, created_by, change_note)` - Rollback
- `export_transcript(transcript_id, format_name, output_path, version, **options)` - Export
- `delete_old_versions(transcript_id, keep_count)` - Cleanup
- `get_version_history(transcript_id)` - Complete history
- `get_statistics()` - System statistics

### FormatConverter

#### Methods

- `to_srt(segments)` - Convert to SRT
- `to_vtt(segments, metadata)` - Convert to VTT
- `to_json(segments, text, metadata, pretty)` - Convert to JSON
- `to_txt(segments, include_timestamps)` - Convert to plain text
- `to_csv(segments, include_header, delimiter)` - Convert to CSV
- `convert(segments, format_name, **kwargs)` - Universal converter
- `validate_segments(segments)` - Validate segment structure
- `get_format_info(format_name)` - Get format details
- `get_supported_formats()` - List supported formats

### DiffGenerator

#### Methods

- `text_diff(old_text, new_text)` - Calculate text differences
- `segment_diff(old_segments, new_segments)` - Calculate segment differences

## Troubleshooting

### Issue: Segments validation fails
```python
# Check segment structure
from src.data import FormatConverter

if not FormatConverter.validate_segments(segments):
    for i, seg in enumerate(segments):
        if 'start' not in seg or 'end' not in seg or 'text' not in seg:
            print(f"Segment {i} missing required keys")
        elif seg['end'] < seg['start']:
            print(f"Segment {i} has invalid timestamps")
```

### Issue: Version not found
```python
# Check available versions
versions = tm.get_versions(transcript_id)
print(f"Available versions: {[v['version_number'] for v in versions]}")
```

### Issue: Export format error
```python
# Check supported formats
supported = FormatConverter.get_supported_formats()
print(f"Supported formats: {supported}")
```

## License

Part of FRISCO WHISPER RTX 5xxx project.
