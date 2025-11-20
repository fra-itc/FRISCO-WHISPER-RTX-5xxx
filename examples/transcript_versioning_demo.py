#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - Transcript Versioning Demo
Demonstrates the transcript management and versioning system

This example shows:
1. Saving transcripts with automatic version 1 creation
2. Updating transcripts (creates new versions automatically)
3. Viewing version history
4. Comparing different versions
5. Exporting to multiple formats (SRT, VTT, JSON, TXT, CSV)
6. Rolling back to previous versions
7. Managing version retention
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import DatabaseManager, TranscriptManager, FormatConverter
from datetime import datetime
import json


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def main():
    """Run the transcript versioning demonstration."""

    # Initialize managers
    print_section("Initializing Transcript Management System")
    db = DatabaseManager('database/transcription.db')
    tm = TranscriptManager(db)
    print("✓ Database and TranscriptManager initialized")

    # Sample data
    sample_segments_v1 = [
        {
            "start": 0.0,
            "end": 5.5,
            "text": "Welcome to FRISCO WHISPER RTX."
        },
        {
            "start": 5.5,
            "end": 12.0,
            "text": "This is a demonstration of the transcript versioning system."
        },
        {
            "start": 12.0,
            "end": 18.5,
            "text": "We can save transcripts and track all changes over time."
        }
    ]

    sample_text_v1 = " ".join([s['text'] for s in sample_segments_v1])

    # ========================================================================
    # Step 1: Create a job and save initial transcript
    # ========================================================================
    print_section("Step 1: Creating Initial Transcript")

    # Create a dummy job for the demo
    job_id = db.create_job(
        file_path=str(Path(__file__).parent / "demo_audio.mp3"),
        model_size='medium',
        language='en'
    )
    print(f"Created job: {job_id}")

    # Save transcript (automatically creates version 1)
    transcript_id = tm.save_transcript(
        job_id=job_id,
        text=sample_text_v1,
        segments=sample_segments_v1,
        language='en',
        created_by='demo_user'
    )
    print(f"✓ Transcript saved with ID: {transcript_id}")
    print(f"  - Version 1 automatically created")
    print(f"  - Segments: {len(sample_segments_v1)}")
    print(f"  - Text length: {len(sample_text_v1)} characters")

    # ========================================================================
    # Step 2: Retrieve and display current transcript
    # ========================================================================
    print_section("Step 2: Retrieving Current Transcript")

    current = tm.get_transcript(transcript_id)
    print(f"Transcript ID: {current['id']}")
    print(f"Job ID: {current['job_id']}")
    print(f"Language: {current['language']}")
    print(f"Current Version: {current['version_number']}")
    print(f"Created by: {current['created_by']}")
    print(f"Created at: {current['version_created_at']}")
    print(f"\nText preview:")
    print(f"  {current['text'][:100]}...")

    # ========================================================================
    # Step 3: Update transcript (creates version 2)
    # ========================================================================
    print_section("Step 3: Updating Transcript (Creates Version 2)")

    # Simulate improved transcription
    sample_segments_v2 = [
        {
            "start": 0.0,
            "end": 5.5,
            "text": "Welcome to FRISCO WHISPER RTX 5000 series."
        },
        {
            "start": 5.5,
            "end": 12.0,
            "text": "This is a demonstration of our advanced transcript versioning system."
        },
        {
            "start": 12.0,
            "end": 18.5,
            "text": "We can save transcripts and automatically track all changes over time."
        },
        {
            "start": 18.5,
            "end": 24.0,
            "text": "This allows for iterative improvement and full history preservation."
        }
    ]

    sample_text_v2 = " ".join([s['text'] for s in sample_segments_v2])

    version_2 = tm.update_transcript(
        transcript_id=transcript_id,
        text=sample_text_v2,
        segments=sample_segments_v2,
        created_by='demo_user',
        change_note='Improved accuracy and added missing segment'
    )
    print(f"✓ Transcript updated to version {version_2}")
    print(f"  - Segments: {len(sample_segments_v2)} (was {len(sample_segments_v1)})")
    print(f"  - Text length: {len(sample_text_v2)} characters (was {len(sample_text_v1)})")
    print(f"  - Change note: 'Improved accuracy and added missing segment'")

    # ========================================================================
    # Step 4: View version history
    # ========================================================================
    print_section("Step 4: Viewing Version History")

    versions = tm.get_versions(transcript_id)
    print(f"Total versions: {len(versions)}\n")

    for v in versions:
        print(f"Version {v['version_number']}:")
        print(f"  - Created: {v['created_at']}")
        print(f"  - Created by: {v['created_by']}")
        print(f"  - Change note: {v['change_note']}")
        print(f"  - Segments: {v['segment_count']}")
        print(f"  - Text length: {v['text_length']} characters")
        print(f"  - Current: {'Yes' if v['is_current'] else 'No'}")
        print()

    # ========================================================================
    # Step 5: Compare versions
    # ========================================================================
    print_section("Step 5: Comparing Versions")

    comparison = tm.compare_versions(transcript_id, version1=1, version2=2)

    print("Text Differences:")
    text_diff = comparison['text_diff']
    print(f"  - Character count: {text_diff['old_length']} → {text_diff['new_length']} "
          f"({text_diff['char_diff']:+d})")
    print(f"  - Word count: {text_diff['old_word_count']} → {text_diff['new_word_count']} "
          f"({text_diff['word_diff']:+d})")

    print("\nSegment Differences:")
    seg_diff = comparison['segment_diff']
    print(f"  - Segment count: {seg_diff['old_segment_count']} → {seg_diff['new_segment_count']} "
          f"({seg_diff['segment_diff']:+d})")
    print(f"  - Duration: {seg_diff['old_duration']:.1f}s → {seg_diff['new_duration']:.1f}s")
    print(f"  - Matching segments: {seg_diff['matching_segments']}")
    print(f"  - Changed segments: {seg_diff['changed_segments']}")
    print(f"  - Similarity: {seg_diff['similarity_percent']:.1f}%")

    # ========================================================================
    # Step 6: Export to multiple formats
    # ========================================================================
    print_section("Step 6: Exporting to Multiple Formats")

    export_dir = Path(__file__).parent / "exports"
    export_dir.mkdir(exist_ok=True)

    formats = ['srt', 'vtt', 'json', 'txt', 'csv']

    for fmt in formats:
        output_file = export_dir / f"transcript_v2.{fmt}"
        content = tm.export_transcript(
            transcript_id=transcript_id,
            format_name=fmt,
            output_path=str(output_file)
        )

        # Get format info
        info = FormatConverter.get_format_info(fmt)
        print(f"✓ Exported to {fmt.upper()}: {output_file.name}")
        print(f"  - Format: {info['name']}")
        print(f"  - MIME type: {info['mime_type']}")
        print(f"  - Size: {len(content)} bytes")

    # Show preview of SRT format
    print("\nSRT Format Preview (first 200 characters):")
    srt_content = tm.export_transcript(transcript_id, 'srt')
    print(f"  {srt_content[:200]}...")

    # ========================================================================
    # Step 7: Create version 3 with manual edits
    # ========================================================================
    print_section("Step 7: Creating Version 3 with Manual Edits")

    sample_segments_v3 = [
        {
            "start": 0.0,
            "end": 5.5,
            "text": "Welcome to FRISCO WHISPER RTX 5000 series!"
        },
        {
            "start": 5.5,
            "end": 12.0,
            "text": "This is a demonstration of our advanced transcript versioning system."
        },
        {
            "start": 12.0,
            "end": 18.5,
            "text": "We can save transcripts and automatically track all changes over time."
        },
        {
            "start": 18.5,
            "end": 24.0,
            "text": "This allows for iterative improvement and full history preservation."
        }
    ]

    sample_text_v3 = " ".join([s['text'] for s in sample_segments_v3])

    version_3 = tm.update_transcript(
        transcript_id=transcript_id,
        text=sample_text_v3,
        segments=sample_segments_v3,
        created_by='editor',
        change_note='Added punctuation and minor formatting improvements'
    )
    print(f"✓ Created version {version_3}")
    print(f"  - Change note: 'Added punctuation and minor formatting improvements'")

    # ========================================================================
    # Step 8: Export specific version
    # ========================================================================
    print_section("Step 8: Exporting Specific Version")

    # Export version 1 for comparison
    v1_file = export_dir / "transcript_v1.srt"
    v1_content = tm.export_transcript(
        transcript_id=transcript_id,
        format_name='srt',
        output_path=str(v1_file),
        version=1
    )
    print(f"✓ Exported version 1 to: {v1_file.name}")

    # Export current version
    current_file = export_dir / "transcript_current.srt"
    current_content = tm.export_transcript(
        transcript_id=transcript_id,
        format_name='srt',
        output_path=str(current_file)
    )
    print(f"✓ Exported current version to: {current_file.name}")

    # ========================================================================
    # Step 9: Rollback to previous version
    # ========================================================================
    print_section("Step 9: Rolling Back to Previous Version")

    print("Current state before rollback:")
    current = tm.get_transcript(transcript_id)
    print(f"  - Version: {current['version_number']}")
    print(f"  - Text preview: {current['text'][:60]}...")

    # Rollback to version 2
    rollback_version = tm.rollback_to_version(
        transcript_id=transcript_id,
        version_number=2,
        created_by='demo_user',
        change_note='Rolled back to version 2 for demonstration'
    )

    print(f"\n✓ Rolled back to version 2")
    print(f"  - New version created: {rollback_version}")
    print(f"  - This preserves history while restoring old content")

    # Verify rollback
    current = tm.get_transcript(transcript_id)
    v2 = tm.get_transcript(transcript_id, version=2)

    print(f"\nVerification:")
    print(f"  - Current version number: {current['version_number']}")
    print(f"  - Content matches version 2: {current['text'] == v2['text']}")

    # ========================================================================
    # Step 10: View complete version history
    # ========================================================================
    print_section("Step 10: Complete Version History")

    history = tm.get_version_history(transcript_id)

    print(f"Transcript ID: {history['transcript_id']}")
    print(f"Job ID: {history['job_id']}")
    print(f"Language: {history['language']}")
    print(f"Total versions: {history['version_count']}")
    print(f"Current version: {history['current_version']}")
    print(f"Total exports: {history['export_count']}")

    print("\nVersion Timeline:")
    for v in history['versions']:
        marker = "→" if v['is_current'] else " "
        print(f"{marker} v{v['version_number']}: {v['change_note']} "
              f"({v['created_by']}, {v['created_at']})")

    if history['exports']:
        print("\nExport History:")
        for exp in history['exports'][:5]:  # Show last 5 exports
            version_str = f"v{exp['version_number']}" if exp['version_number'] else "current"
            print(f"  - {exp['format_name'].upper()} ({version_str}) at {exp['exported_at']}")

    # ========================================================================
    # Step 11: Manage version retention
    # ========================================================================
    print_section("Step 11: Version Retention Management")

    print(f"Current version count: {len(tm.get_versions(transcript_id))}")
    print(f"Setting retention policy to keep last 3 versions...")

    deleted = tm.delete_old_versions(transcript_id, keep_count=3)

    print(f"✓ Deleted {deleted} old version(s)")
    print(f"Remaining versions: {len(tm.get_versions(transcript_id))}")

    remaining = tm.get_versions(transcript_id)
    print(f"\nRetained versions:")
    for v in remaining:
        print(f"  - Version {v['version_number']}: {v['change_note']}")

    # ========================================================================
    # Step 12: Statistics and summary
    # ========================================================================
    print_section("Step 12: System Statistics")

    stats = tm.get_statistics()

    print("Transcript Statistics:")
    print(f"  - Total transcripts: {stats.get('total_transcripts', 0)}")
    print(f"  - Total versions: {stats.get('total_versions', 0)}")
    print(f"  - Average versions per transcript: {stats.get('avg_versions_per_transcript', 0):.2f}")
    print(f"  - Maximum versions: {stats.get('max_versions', 0)}")
    print(f"  - Total exports: {stats.get('total_exports', 0)}")
    print(f"  - Export formats used: {stats.get('formats_used', 0)}")

    if stats.get('exports_by_format'):
        print("\nExports by format:")
        for fmt, count in stats['exports_by_format'].items():
            print(f"  - {fmt.upper()}: {count}")

    # ========================================================================
    # Conclusion
    # ========================================================================
    print_section("Demo Complete!")

    print("This demonstration showed:")
    print("  ✓ Automatic version creation on save and update")
    print("  ✓ Complete version history tracking")
    print("  ✓ Version comparison and diff generation")
    print("  ✓ Export to multiple formats (SRT, VTT, JSON, TXT, CSV)")
    print("  ✓ Exporting specific versions")
    print("  ✓ Rollback to previous versions")
    print("  ✓ Version retention management")
    print("  ✓ System statistics and reporting")

    print(f"\nExported files can be found in: {export_dir.absolute()}")
    print("\nThe versioning system ensures:")
    print("  • Non-destructive updates (all history preserved)")
    print("  • Full audit trail with user attribution")
    print("  • Flexible export options")
    print("  • Easy rollback mechanism")
    print("  • Configurable retention policies")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
