"""
Novel Translation Tool Package.

This package provides tools for:
- Chapter splitting and combining
- Text translation using Gemini API
- Proofreading and OCR
- Folder management
"""

__version__ = "1.0.0"

# Import main components
from .translation import main as translation_main
from .chapter_splitting_tools import (
    EpubSeparator,
    NovelSplitter,
    OutputCombiner,
    FolderManager
)

__all__ = [
    'translation_main',
    'EpubSeparator',
    'NovelSplitter',
    'OutputCombiner',
    'FolderManager'
]
