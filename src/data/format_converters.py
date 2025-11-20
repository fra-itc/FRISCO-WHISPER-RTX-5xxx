#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - Format Converters
Converts transcription data between different subtitle and text formats
"""

import json
import csv
import io
from typing import List, Dict, Any, Optional
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class FormatConverter:
    """
    Converts transcription segments to various output formats.

    Supported formats:
    - SRT: SubRip subtitle format
    - VTT: WebVTT web video text tracks
    - JSON: Structured JSON with full segment data
    - TXT: Plain text without timestamps
    - CSV: Tabular format with timestamps
    """

    @staticmethod
    def _format_timestamp_srt(seconds: float) -> str:
        """
        Format seconds to SRT timestamp format (HH:MM:SS,mmm).

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp string
        """
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        millis = int((td.total_seconds() % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def _format_timestamp_vtt(seconds: float) -> str:
        """
        Format seconds to VTT timestamp format (HH:MM:SS.mmm).

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp string
        """
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        millis = int((td.total_seconds() % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    @staticmethod
    def _format_timestamp_human(seconds: float) -> str:
        """
        Format seconds to human-readable timestamp (HH:MM:SS).

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp string
        """
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    @classmethod
    def to_srt(cls, segments: List[Dict[str, Any]]) -> str:
        """
        Convert segments to SRT subtitle format.

        SRT Format:
        1
        00:00:00,000 --> 00:00:05,000
        First subtitle text

        2
        00:00:05,000 --> 00:00:10,000
        Second subtitle text

        Args:
            segments: List of segment dictionaries with 'start', 'end', 'text' keys

        Returns:
            SRT formatted string
        """
        if not segments:
            logger.warning("No segments provided for SRT conversion")
            return ""

        srt_lines = []

        for index, segment in enumerate(segments, start=1):
            start = segment.get('start', 0)
            end = segment.get('end', 0)
            text = segment.get('text', '').strip()

            if not text:
                continue

            # Sequence number
            srt_lines.append(str(index))

            # Timestamp line
            start_ts = cls._format_timestamp_srt(start)
            end_ts = cls._format_timestamp_srt(end)
            srt_lines.append(f"{start_ts} --> {end_ts}")

            # Text content
            srt_lines.append(text)

            # Blank line separator
            srt_lines.append("")

        result = "\n".join(srt_lines)
        logger.debug(f"Converted {len(segments)} segments to SRT format")
        return result

    @classmethod
    def to_vtt(cls, segments: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Convert segments to WebVTT format.

        VTT Format:
        WEBVTT

        00:00:00.000 --> 00:00:05.000
        First subtitle text

        00:00:05.000 --> 00:00:10.000
        Second subtitle text

        Args:
            segments: List of segment dictionaries with 'start', 'end', 'text' keys
            metadata: Optional metadata dict (language, title, etc.)

        Returns:
            VTT formatted string
        """
        if not segments:
            logger.warning("No segments provided for VTT conversion")
            return "WEBVTT\n\n"

        vtt_lines = ["WEBVTT"]

        # Add optional metadata
        if metadata:
            if 'language' in metadata:
                vtt_lines.append(f"Language: {metadata['language']}")
            if 'title' in metadata:
                vtt_lines.append(f"Title: {metadata['title']}")

        vtt_lines.append("")  # Blank line after header

        for segment in segments:
            start = segment.get('start', 0)
            end = segment.get('end', 0)
            text = segment.get('text', '').strip()

            if not text:
                continue

            # Timestamp line (no sequence number in VTT)
            start_ts = cls._format_timestamp_vtt(start)
            end_ts = cls._format_timestamp_vtt(end)
            vtt_lines.append(f"{start_ts} --> {end_ts}")

            # Text content
            vtt_lines.append(text)

            # Blank line separator
            vtt_lines.append("")

        result = "\n".join(vtt_lines)
        logger.debug(f"Converted {len(segments)} segments to VTT format")
        return result

    @staticmethod
    def to_json(
        segments: List[Dict[str, Any]],
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        pretty: bool = True
    ) -> str:
        """
        Convert segments to structured JSON format.

        Args:
            segments: List of segment dictionaries
            text: Optional full text content
            metadata: Optional metadata (language, duration, etc.)
            pretty: Whether to format JSON with indentation

        Returns:
            JSON formatted string
        """
        if not segments:
            logger.warning("No segments provided for JSON conversion")

        data = {
            "format": "whisper-json",
            "version": "1.0",
            "metadata": metadata or {},
            "text": text or "",
            "segment_count": len(segments),
            "segments": segments
        }

        indent = 2 if pretty else None
        result = json.dumps(data, ensure_ascii=False, indent=indent)

        logger.debug(f"Converted {len(segments)} segments to JSON format")
        return result

    @staticmethod
    def to_txt(segments: List[Dict[str, Any]], include_timestamps: bool = False) -> str:
        """
        Convert segments to plain text format.

        Args:
            segments: List of segment dictionaries
            include_timestamps: Whether to include timestamps in brackets

        Returns:
            Plain text string
        """
        if not segments:
            logger.warning("No segments provided for TXT conversion")
            return ""

        lines = []

        for segment in segments:
            text = segment.get('text', '').strip()

            if not text:
                continue

            if include_timestamps:
                start = segment.get('start', 0)
                timestamp = FormatConverter._format_timestamp_human(start)
                lines.append(f"[{timestamp}] {text}")
            else:
                lines.append(text)

        result = "\n".join(lines)
        logger.debug(f"Converted {len(segments)} segments to TXT format")
        return result

    @classmethod
    def to_csv(
        cls,
        segments: List[Dict[str, Any]],
        include_header: bool = True,
        delimiter: str = ','
    ) -> str:
        """
        Convert segments to CSV format.

        CSV Format:
        index,start,end,duration,text
        1,0.0,5.0,5.0,"First segment text"
        2,5.0,10.0,5.0,"Second segment text"

        Args:
            segments: List of segment dictionaries
            include_header: Whether to include header row
            delimiter: CSV delimiter character

        Returns:
            CSV formatted string
        """
        if not segments:
            logger.warning("No segments provided for CSV conversion")
            return ""

        output = io.StringIO(newline='')
        fieldnames = ['index', 'start', 'end', 'duration', 'text']

        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            delimiter=delimiter,
            quoting=csv.QUOTE_MINIMAL,
            lineterminator='\n'
        )

        if include_header:
            writer.writeheader()

        for index, segment in enumerate(segments, start=1):
            start = segment.get('start', 0)
            end = segment.get('end', 0)
            duration = end - start
            text = segment.get('text', '').strip()

            if not text:
                continue

            writer.writerow({
                'index': index,
                'start': f"{start:.3f}",
                'end': f"{end:.3f}",
                'duration': f"{duration:.3f}",
                'text': text
            })

        result = output.getvalue()
        output.close()

        logger.debug(f"Converted {len(segments)} segments to CSV format")
        return result

    @staticmethod
    def from_json(json_str: str) -> Dict[str, Any]:
        """
        Parse JSON format back to segments and metadata.

        Args:
            json_str: JSON formatted string

        Returns:
            Dictionary with 'segments', 'text', 'metadata' keys
        """
        try:
            data = json.loads(json_str)

            return {
                'segments': data.get('segments', []),
                'text': data.get('text', ''),
                'metadata': data.get('metadata', {})
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise ValueError(f"Invalid JSON format: {e}")

    @staticmethod
    def get_supported_formats() -> List[str]:
        """
        Get list of supported export formats.

        Returns:
            List of format names
        """
        return ['srt', 'vtt', 'json', 'txt', 'csv']

    @classmethod
    def convert(
        cls,
        segments: List[Dict[str, Any]],
        format_name: str,
        **kwargs
    ) -> str:
        """
        Convert segments to specified format.

        Args:
            segments: List of segment dictionaries
            format_name: Target format (srt, vtt, json, txt, csv)
            **kwargs: Additional format-specific options

        Returns:
            Formatted string

        Raises:
            ValueError: If format is not supported
        """
        format_name = format_name.lower()

        converters = {
            'srt': cls.to_srt,
            'vtt': cls.to_vtt,
            'json': cls.to_json,
            'txt': cls.to_txt,
            'csv': cls.to_csv
        }

        if format_name not in converters:
            raise ValueError(
                f"Unsupported format: {format_name}. "
                f"Supported formats: {', '.join(cls.get_supported_formats())}"
            )

        converter = converters[format_name]
        return converter(segments, **kwargs)

    @staticmethod
    def validate_segments(segments: List[Dict[str, Any]]) -> bool:
        """
        Validate segment structure.

        Args:
            segments: List of segment dictionaries

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(segments, list):
            logger.error("Segments must be a list")
            return False

        for i, segment in enumerate(segments):
            if not isinstance(segment, dict):
                logger.error(f"Segment {i} is not a dictionary")
                return False

            required_keys = ['start', 'end', 'text']
            for key in required_keys:
                if key not in segment:
                    logger.error(f"Segment {i} missing required key: {key}")
                    return False

            # Validate timestamps
            start = segment.get('start')
            end = segment.get('end')

            if not isinstance(start, (int, float)) or start < 0:
                logger.error(f"Segment {i} has invalid start time: {start}")
                return False

            if not isinstance(end, (int, float)) or end < 0:
                logger.error(f"Segment {i} has invalid end time: {end}")
                return False

            if end < start:
                logger.error(f"Segment {i} end time before start time")
                return False

        return True

    @staticmethod
    def get_format_info(format_name: str) -> Dict[str, str]:
        """
        Get information about a specific format.

        Args:
            format_name: Format name

        Returns:
            Dictionary with format details
        """
        formats = {
            'srt': {
                'name': 'SubRip',
                'extension': '.srt',
                'mime_type': 'application/x-subrip',
                'description': 'Standard subtitle format widely supported'
            },
            'vtt': {
                'name': 'WebVTT',
                'extension': '.vtt',
                'mime_type': 'text/vtt',
                'description': 'Web video text tracks for HTML5'
            },
            'json': {
                'name': 'JSON',
                'extension': '.json',
                'mime_type': 'application/json',
                'description': 'Structured data with full segment information'
            },
            'txt': {
                'name': 'Plain Text',
                'extension': '.txt',
                'mime_type': 'text/plain',
                'description': 'Simple text format without timestamps'
            },
            'csv': {
                'name': 'CSV',
                'extension': '.csv',
                'mime_type': 'text/csv',
                'description': 'Tabular format with timestamps and text'
            }
        }

        return formats.get(format_name.lower(), {})


class DiffGenerator:
    """Generate diffs between different versions of transcripts."""

    @staticmethod
    def text_diff(old_text: str, new_text: str) -> Dict[str, Any]:
        """
        Calculate simple text difference statistics.

        Args:
            old_text: Original text
            new_text: Modified text

        Returns:
            Dictionary with diff statistics
        """
        old_words = old_text.split()
        new_words = new_text.split()

        old_chars = len(old_text)
        new_chars = len(new_text)

        # Calculate Levenshtein distance at word level
        word_changes = abs(len(old_words) - len(new_words))

        return {
            'old_length': old_chars,
            'new_length': new_chars,
            'char_diff': new_chars - old_chars,
            'old_word_count': len(old_words),
            'new_word_count': len(new_words),
            'word_diff': len(new_words) - len(old_words),
            'estimated_changes': word_changes
        }

    @staticmethod
    def segment_diff(
        old_segments: List[Dict[str, Any]],
        new_segments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate differences between segment lists.

        Args:
            old_segments: Original segments
            new_segments: Modified segments

        Returns:
            Dictionary with segment diff statistics
        """
        old_count = len(old_segments)
        new_count = len(new_segments)

        # Calculate total duration for both versions
        old_duration = old_segments[-1]['end'] if old_segments else 0
        new_duration = new_segments[-1]['end'] if new_segments else 0

        # Count matching segments (same start time and text)
        old_dict = {(s['start'], s['text']): s for s in old_segments}
        new_dict = {(s['start'], s['text']): s for s in new_segments}

        common_keys = set(old_dict.keys()) & set(new_dict.keys())
        matching_segments = len(common_keys)

        return {
            'old_segment_count': old_count,
            'new_segment_count': new_count,
            'segment_diff': new_count - old_count,
            'old_duration': old_duration,
            'new_duration': new_duration,
            'duration_diff': new_duration - old_duration,
            'matching_segments': matching_segments,
            'changed_segments': old_count + new_count - 2 * matching_segments,
            'similarity_percent': (matching_segments / max(old_count, new_count) * 100) if max(old_count, new_count) > 0 else 0
        }
