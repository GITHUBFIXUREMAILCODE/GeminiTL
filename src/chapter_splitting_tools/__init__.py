"""
Chapter splitting tools package for the novel translation tool.

This package provides functionality for:
- EPUB chapter separation
- Novel text splitting
- Output file combination
- Folder management
"""

from .epub_separator import EPUBSeparator
from .novel_splitter import TextSplitterApp
from .output_combiner import OutputCombiner
from .folder_manager import FolderManager

__all__ = [
    'EPUBSeparator',
    'TextSplitterApp',
    'OutputCombiner',
    'FolderManager'
]
