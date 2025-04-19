"""
Translation package for the novel translation tool.

This package provides functionality for:
- Text translation using Gemini API
- Glossary management
- Proofreading
- Image OCR and processing
"""

from .translator import Translator
from .glossary import Glossary
from .proofing import Proofreader
from .image_ocr import ImageOCR
from .ocr_fail_detection import OCRFailDetector
from .main_ph import main

__all__ = [
    'Translator',
    'Glossary',
    'Proofreader',
    'ImageOCR',
    'OCRFailDetector',
    'main'
]
