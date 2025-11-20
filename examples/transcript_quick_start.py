#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - Transcript Versioning Quick Start
Minimal example showing basic versioning features
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import DatabaseManager, TranscriptManager

# Initialize
db = DatabaseManager('database/transcription.db')
tm = TranscriptManager(db)

# Example segments (normally from Whisper transcription)
segments = [
    {"start": 0.0, "end": 3.5, "text": "Welcome to the tutorial."},
    {"start": 3.5, "end": 7.0, "text": "Today we'll learn about versioning."},
    {"start": 7.0, "end": 11.5, "text": "Every change is tracked automatically."}
]
full_text = " ".join([s['text'] for s in segments])

# Create a job (normally done by transcription pipeline)
job_id = '12345-example'  # UUID from actual transcription job

# Save transcript - creates version 1 automatically
print("1. Saving initial transcript...")
transcript_id = tm.save_transcript(
    job_id=job_id,
    text=full_text,
    segments=segments,
    language='en',
    created_by='tutorial_user'
)
print(f"   ✓ Transcript saved with ID: {transcript_id}")

# Update transcript - creates version 2 automatically
print("\n2. Updating transcript (creates version 2)...")
updated_segments = segments.copy()
updated_segments[1]['text'] = "Today we'll learn about automatic versioning."
updated_text = " ".join([s['text'] for s in updated_segments])

version_num = tm.update_transcript(
    transcript_id=transcript_id,
    text=updated_text,
    segments=updated_segments,
    created_by='tutorial_user',
    change_note='Clarified versioning description'
)
print(f"   ✓ Updated to version: {version_num}")

# View version history
print("\n3. Version history:")
versions = tm.get_versions(transcript_id)
for v in versions:
    current_marker = "→" if v['is_current'] else " "
    print(f"   {current_marker} Version {v['version_number']}: {v['change_note']} "
          f"(by {v['created_by']})")

# Export to different formats
print("\n4. Exporting to multiple formats...")
output_dir = Path('transcripts')
output_dir.mkdir(exist_ok=True)

for format_name in ['srt', 'vtt', 'json', 'txt']:
    output_path = output_dir / f'transcript.{format_name}'
    tm.export_transcript(transcript_id, format_name, str(output_path))
    print(f"   ✓ Exported: {output_path}")

# Compare versions
print("\n5. Comparing versions 1 and 2...")
comparison = tm.compare_versions(transcript_id, version1=1, version2=2)
print(f"   Text change: {comparison['text_diff']['char_diff']:+d} characters")
print(f"   Segment change: {comparison['segment_diff']['segment_diff']:+d} segments")
print(f"   Similarity: {comparison['segment_diff']['similarity_percent']:.1f}%")

# Get specific version
print("\n6. Retrieving version 1...")
v1 = tm.get_transcript(transcript_id, version=1)
print(f"   Text: {v1['text'][:50]}...")

print("\n✓ Quick start complete!")
print(f"\nYou now have:")
print(f"  - {len(versions)} versions stored")
print(f"  - 4 export formats in {output_dir}/")
print(f"  - Complete version history")
print(f"\nSee examples/transcript_versioning_demo.py for advanced features!")
