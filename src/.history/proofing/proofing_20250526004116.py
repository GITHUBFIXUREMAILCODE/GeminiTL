
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
        Detects non-English lines in all .txt files in the folder, retranslates them via Gemini, and logs both issues and fixes.
        """
        flagged = []

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

            flagged_lines = non_english_checker.detect_non_english_lines(lines)
            if not flagged_lines:
                continue

            glossary_text = ""
            if self.glossary_path:
                try:
                    with open(self.glossary_path, "r", encoding="utf-8") as f:
                        glossary_text = f.read()
                except Exception as e:
                    self.log_message(f"[ERROR] Failed to load glossary: {e}")

            indices, targets = zip(*flagged_lines)
            fixed = non_english_checker.batch_retranslate(targets, glossary_text, log_message=self.log_message)

            if fixed is None:
                self.log_message(f"[FAILED] Could not fix lines in {fname}")
                continue

            updated_lines = list(lines)
            for i, (idx, fixed_line) in enumerate(zip(indices, fixed)):
                flagged.append(f"{fname} (line {idx + 1}): {lines[idx].strip()}")
                updated_lines[idx] = fixed_line + "\n" if not fixed_line.endswith("\n") else fixed_line

                self.log_message(f"[NON-ENGLISH] {fname} (line {idx + 1}):")
                self.log_message(f"  ⛔ {lines[idx].strip()}")
                self.log_message(f"  ✅ {fixed_line.strip()}")

            with open(path, "w", encoding="utf-8") as f:
                f.writelines(updated_lines)

            self.log_message(f"[NON-ENGLISH] Updated {len(fixed)} lines in {fname}")

        if flagged:
            try:
                with open(log_path, "w", encoding="utf-8") as logf:
                    logf.write("\n".join(flagged))
                self.log_message(f"[OK] Logged non-English issues to: {log_path}")
            except Exception as e:
                self.log_message(f"[ERROR] Could not write log to {log_path}: {e}")
        else:
            self.log_message("[OK] No non-English lines found.")

        return flagged
