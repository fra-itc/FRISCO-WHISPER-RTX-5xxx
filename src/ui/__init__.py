#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - Web UI Module
FastAPI-based web interface for transcription management
"""

from .web_server import app, main

__all__ = ['app', 'main']
__version__ = '1.3.0'
