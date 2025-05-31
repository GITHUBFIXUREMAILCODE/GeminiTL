"""
Module: proofing.py

Coordinator for all proofreading operations (gender, glossary, style, and non-English detection).
"""

import os
from . import gender_proofing
from . import glossary_proofing
from . import ai_proofreader
from . import non_english_checker
from .glossary_utils import get_matched_context_glossary_entries
from .utils import contains_non_english_letters

from typing import Optional
class Proofreader:
    def __init__(self, log_message=None, glossary_path=None):
        self.log_message = log_message or print
        self.glossary_path = glossary_path

    def proof_gender_pronouns(self, text: str, context_dict: dict, glossary_path: Optional[str] = None, **kwargs):
        glossary_path = glossary_path or self.glossary_path
        return gender_proofing.proof_gender_pronouns(
            text,
            context_dict,
            glossary_path,
            log_message=self.log_message,
            **kwargs
        )

    def detect_and_fix_non_english(self, lines, glossary_text="", **kwargs):
        """
        Detect and retranslate non-English lines in a list of lines.
        Returns the updated list or None if failed.
        """
        flagged = non_english_checker.detect_non_english_lines(lines)
        if not flagged:
            self.log_message("[CHECK] No non-English lines found.")
            return lines

        indices, targets = zip(*flagged)
        fixed_lines = non_english_checker.batch_retranslate(
            targets, glossary_text=glossary_text, log_message=self.log_message, **kwargs
        )

        if fixed_lines is None:
            return None

        # Apply fixes back to the original list
        updated = list(lines)
        for idx, fixed in zip(indices, fixed_lines):
            updated[idx] = fixed + "\n" if not fixed.endswith("\n") else fixed
        return updated

    def proof_glossary_file(self, glossary_path: Optional[str] = None, **kwargs):
        glossary_path = glossary_path or self.glossary_path
        glossary_proofing.proof_glossary_file(glossary_path, log_message=self.log_message, **kwargs)

    def proofread_with_ai(self, file_path: str, glossary_path: Optional[str] = None, **kwargs):
        return ai_proofreader.proofread_with_ai(
            file_path,
            glossary_path=self.glossary_path,
            log_message=self.log_message,
            **kwargs
        )

    def load_context_glossary(self, glossary_path: Optional[str] = None):
        glossary_path = glossary_path or self.glossary_path
        return get_matched_context_glossary_entries(glossary_path, "", log=self.log_message)

    def contains_non_english_letters(self, text):
        return contains_non_english_letters(text)
