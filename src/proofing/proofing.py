
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

    def detect_and_log_non_english_sentences(self, folder: str, log_path: str, reference_folder: str = "", pause_event=None, cancel_flag=None):
        """
        Detects all non-English lines across all files, retranslates them in a single batch, and replaces in-place.
        """
        global_flagged = []  # List of (fname, index, line)
        file_lines = {}      # fname -> List[str]

        # 1. Collect all non-English lines
        for fname in os.listdir(folder):
            if not fname.endswith(".txt"):
                continue

            if cancel_flag and cancel_flag():
                self.log_message("[CONTROL] Cancel requested during non-English check.")
                break

            if pause_event and not pause_event.is_set():
                self.log_message("[CONTROL] Paused during non-English check.")
                pause_event.wait()
                self.log_message("[CONTROL] Resumed.")

            path = os.path.join(folder, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception as e:
                self.log_message(f"[ERROR] Failed to read {fname}: {e}")
                continue

            file_lines[fname] = lines
            for idx, line in non_english_checker.detect_non_english_lines(lines):
                global_flagged.append((fname, idx, line))

        if not global_flagged:
            self.log_message("[OK] No non-English lines found.")
            return []

        glossary_text = ""
        if self.glossary_path:
            try:
                with open(self.glossary_path, "r", encoding="utf-8") as f:
                    glossary_text = f.read()
            except Exception as e:
                self.log_message(f"[ERROR] Failed to load glossary: {e}")

        # 2. Translate all flagged lines in one call
        original_lines = [line.strip() for (_, _, line) in global_flagged]
        fixed_lines = non_english_checker.batch_retranslate(original_lines, glossary_text, log_message=self.log_message)

        if fixed_lines is None:
            self.log_message("[FAILED] Retranslation failed. No files updated.")
            return []

        # 3. Replace fixed lines into their files
        flagged_log = []
        for (fname, idx, orig), fixed in zip(global_flagged, fixed_lines):
            lines = file_lines[fname]
            old = lines[idx].strip()
            lines[idx] = fixed + "\n" if not fixed.endswith("\n") else fixed

            self.log_message(f"[NON-ENGLISH] {fname} (line {idx+1}):")
            self.log_message(f"  ⛔ {old}")
            self.log_message(f"  ✅ {fixed.strip()}")

            flagged_log.append(f"{fname} (line {idx+1}): {old}")

        # 4. Write back updated files
        for fname, lines in file_lines.items():
            with open(os.path.join(folder, fname), "w", encoding="utf-8") as f:
                f.writelines(lines)

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(flagged_log))
        self.log_message(f"[OK] Logged non-English issues to: {log_path}")

        return flagged_log
