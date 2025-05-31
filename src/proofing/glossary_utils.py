"""
Module: glossary_utils.py

Contains utilities for working with glossaries including loading,
matching, and splitting.
"""

import os
import re

def get_matched_context_glossary_entries(glossary_path: str, chapter_text: str, log=print) -> dict:
    """
    Return {name.lower(): gender} for entries in context_glossary.txt that
    actually appear in chapter_text (case-insensitive, word-boundary match).
    """
    matched = {}
    try:
        glossary_name = os.path.splitext(os.path.basename(glossary_path))[0]
        base_dir = os.path.dirname(glossary_path)
        ctx_path = os.path.join(base_dir, glossary_name, "context_glossary.txt")

        with open(ctx_path, "r", encoding="utf-8") as f:
            raw = f.read()
        block = raw.split("==================================== GLOSSARY START ===============================")[1]                    .split("==================================== GLOSSARY END ================================")[0]

        for line in block.splitlines():
            if "=>" not in line:
                continue
            parts = [p.strip() for p in line.split("=>")]
            if len(parts) < 2:
                continue
            original = parts[0]
            gender   = parts[-1]
            if re.search(rf'\b{re.escape(original)}\b', chapter_text, re.IGNORECASE):
                matched[original.lower()] = gender
            if len(parts) == 3:
                translated = parts[1]
                if re.search(rf'\b{re.escape(translated)}\b', chapter_text, re.IGNORECASE):
                    matched[translated.lower()] = gender
    except Exception as e:
        log(f"[GLOSSARY] Context‑matcher error: {e}")
    return matched

def load_full_context_glossary(glossary_path):
    """
    Return the full context glossary block as a string.
    """
    try:
        glossary_name = os.path.splitext(os.path.basename(glossary_path))[0]
        ctx_path = os.path.join(os.path.dirname(glossary_path), glossary_name, "context_glossary.txt")
        with open(ctx_path, "r", encoding="utf-8") as f:
            content = f.read()
        block = content.split("==================================== GLOSSARY START ===============================")[1]                        .split("==================================== GLOSSARY END ================================")[0]
        return block.strip()
    except Exception:
        return ""

def load_proofing_glossaries(glossary_path, log_message=print):
    """
    Loads both the name and context glossaries from the glossary subfolder.
    Returns two strings: name_glossary_text and context_glossary_text.
    """
    glossary_name = os.path.splitext(os.path.basename(glossary_path))[0]
    glossary_dir = os.path.dirname(glossary_path)
    subfolder = os.path.join(glossary_dir, glossary_name)

    name_glossary_path = os.path.join(subfolder, "name_glossary.txt")
    context_glossary_path = os.path.join(subfolder, "context_glossary.txt")

    name_text, context_text = "", ""
    try:
        with open(name_glossary_path, "r", encoding="utf-8") as f:
            name_text = f.read().strip()
    except Exception as e:
        log_message(f"[ERROR] Unable to load name glossary from {name_glossary_path}: {e}")

    try:
        with open(context_glossary_path, "r", encoding="utf-8") as f:
            context_text = f.read().strip()
    except Exception as e:
        log_message(f"[ERROR] Unable to load context glossary from {context_glossary_path}: {e}")

    return name_text, context_text
