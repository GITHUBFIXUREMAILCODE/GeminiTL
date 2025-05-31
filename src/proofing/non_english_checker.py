"""
Module: non_english_checker.py

Performs detection of untranslated lines and batch retranslation using Gemini.
"""

import os
import re
import time
from vertexai.generative_models import GenerativeModel, GenerationConfig
from config.config import SAFETY_SETTING
from .utils import contains_non_english_letters, call_with_timeout

DELIMITER = "====TRANS_UNIT_SEP===="

def detect_non_english_lines(text_lines):
    """
    Returns a list of (index, line) pairs where the line appears to contain non-English characters.
    """
    results = []
    for i, line in enumerate(text_lines):
        line_content = line.strip()
        if line_content and contains_non_english_letters(line_content):
            alphabetic_chars = sum(c.isalpha() for c in line_content)
            if alphabetic_chars > 1:
                results.append((i, line))
    return results

def batch_retranslate(lines, glossary_text="", log_message=print, max_retries=4, initial_retry_delay=60):
    """
    Sends lines to Gemini for selective retranslation.
    """
    system_instruction = "\n".join([
        "You are an expert English translator tasked with fixing lines containing untranslated non-English words or characters.",
        "You will receive text lines separated by '====TRANS_UNIT_SEP===='.",
        "Your PRIMARY GOAL is to translate ONLY the non-English words within each line into fluent English.",
        "CRITICAL RULES:",
        "1. Translate ALL non-English words to proper English meanings in context.",
        "2. DO NOT transliterate. No romanizations allowed.",
        "3. DO NOT explain translations. DO NOT add parentheses or footnotes.",
        "4. DO NOT modify any English, punctuation, names, or formatting.",
        "5. If a line is fully English, return it unchanged.",
        "",
        "Return the revised lines using the exact same delimiter format and order.",
        "Ensure output has the same number of lines as input, one delimiter between each line.",
        "",
        "Glossary (for name consistency):",
        glossary_text or "(none)"
    ])

    input_text = f"{DELIMITER}\n" + f"\n{DELIMITER}\n".join(line.strip() for line in lines)

    model = GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        safety_settings=SAFETY_SETTING,
        system_instruction=system_instruction,
        generation_config=GenerationConfig(
            temperature=0.1,
            top_p=0.90,
            top_k=40,
            response_mime_type="text/plain"
        )
    )

    for attempt in range(max_retries):
        retry_delay = initial_retry_delay * (2 ** attempt)  # Exponential backoff
        
        try:
            # Use call_with_timeout to prevent hanging
            success, result = call_with_timeout(
                model.generate_content, 
                args=(input_text,), 
                timeout=150  # 2.5 minute timeout
            )
            
            if not success:
                if isinstance(result, TimeoutError):
                    log_message(f"[TIMEOUT] Non-English retranslation timed out after 150 seconds")
                else:
                    log_message(f"[ERROR] Non-English retranslation failed: {result}")
                if attempt < max_retries - 1:
                    log_message(f"[RETRY] Waiting {retry_delay}s...")
                    time.sleep(retry_delay)
                continue
                
            response = result
            
            if not response or not response.text:
                log_message("[ERROR] Empty AI response")
                continue

            raw = response.text.strip()
            if raw.startswith(DELIMITER):
                raw = raw[len(DELIMITER):]
            if raw.endswith(DELIMITER):
                raw = raw[:-len(DELIMITER)]

            output_lines = [line.strip() for line in raw.split(DELIMITER)]
            if len(output_lines) != len(lines):
                log_message(f"[ERROR] Line count mismatch: expected {len(lines)}, got {len(output_lines)}")
                continue
            return output_lines
        except Exception as e:
            log_message(f"[ERROR] Retranslation attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    log_message("[FAILED] Retranslation failed after all retries.")
    return None

