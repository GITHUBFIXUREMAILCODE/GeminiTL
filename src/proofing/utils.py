"""
Utility functions shared across the proofing pipeline.
"""

import re
import unicodedata
import threading
from typing import List

def split_into_sentences(text: str) -> List[str]:
    """Basic sentence splitter using punctuation."""
    return re.split(r'(?<=[.!?])\s+', text)

def contains_non_english_letters(text: str) -> bool:
    """
    Return True if 'text' contains any letters that are not LATIN.
    Ignores common Asian symbols and full-width punctuation.
    """
    ignore_chars = set("「」『』【】（）〈〉《》・ー〜～！？、。．，：；“”‘’・…—–‐≪≫〈〉『』【】〔〕（）［］｛｝｢｣ ㄴ ㅡ ㅋ ㅣ")
    for char in text:
        if char in ignore_chars:
            continue
        if char.isalpha():
            name = unicodedata.name(char, "")
            if "LATIN" not in name:
                return True
    return False

def inject_context(input_text: str, context_dict: dict) -> str:
    """
    Inject context as a header for use in debugging or AI prompting.
    """
    injected_lines = [f"{name} is {desc}." for name, desc in context_dict.items()]
    context_header = "Context: " + " ".join(injected_lines)
    return f"{context_header}\n\n{input_text}"

def split_text_into_chunks(text: str, max_bytes: int = 10240) -> List[str]:
    """
    Splits text into chunks of approximately max_bytes size without breaking lines.
    """
    lines = text.splitlines(keepends=True)
    chunks = []
    current_chunk = ''
    current_size = 0

    for line in lines:
        line_size = len(line.encode('utf-8'))
        if current_size + line_size > max_bytes and current_chunk:
            chunks.append(current_chunk)
            current_chunk = ''
            current_size = 0
        current_chunk += line
        current_size += line_size

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def call_with_timeout(func, args=(), kwargs=None, timeout=120):
    """Runs a function with timeout. Returns (success, result or exception)."""
    if kwargs is None:
        kwargs = {}

    result_container = {}

    def wrapper():
        try:
            result_container["result"] = func(*args, **kwargs)
        except Exception as e:
            result_container["exception"] = e

    thread = threading.Thread(target=wrapper)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        return False, TimeoutError(f"Function call exceeded {timeout} seconds.")
    if "exception" in result_container:
        return False, result_container["exception"]
    return True, result_container["result"]

